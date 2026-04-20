"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from collections import defaultdict
from typing import Dict, List

from django.db.models import F

from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import AppCache, Cluster, ClusterEntry, Machine, StorageInstance


def list_my_es_bizs(userID: str) -> List:
    res = []
    for app in AppCache.objects.all():
        bk_biz_id = app.bk_biz_id

        if DBAdministrator.objects.filter(bk_biz_id=bk_biz_id, users__0=userID, db_type=DBType.Es.value):
            res.append({"bk_biz_id": bk_biz_id, "app_name": app.bk_biz_name, "abbr": app.db_app_abbr})
    return res


def list_es_biz_by_name(biz_name: str) -> List:
    res = []
    for app in AppCache.objects.all():
        if app.db_app_abbr.__contains__(biz_name.lower()):
            res.append({"bk_biz_id": app.bk_biz_id, "app_name": app.bk_biz_name, "abbr": app.db_app_abbr})
    return res


def list_es_clusters(bk_biz_id: int) -> List:
    clusters = Cluster.objects.filter(bk_biz_id=bk_biz_id, cluster_type=ClusterType.Es)
    return [
        {
            "cluster_id": c.id,
            "bk_cloud_id": c.bk_cloud_id,
            "cluster_type": c.cluster_type,
            "immute_domain": c.immute_domain,
            "alias": c.alias,
            "region": c.region,
            "master_node_count": len(c.storageinstance_set.filter(instance_role=InstanceRole.ES_MASTER.value)),
            "hot_node_count": len(c.storageinstance_set.filter(instance_role=InstanceRole.ES_DATANODE_HOT.value)),
            "cold_node_count": len(c.storageinstance_set.filter(instance_role=InstanceRole.ES_DATANODE_COLD.value)),
            "client_node_count": len(c.storageinstance_set.filter(instance_role=InstanceRole.ES_CLIENT.value)),
            "es_version": c.major_version,
        }
        for c in clusters
    ]


def get_machine_stats(all_machine_ids) -> Dict:
    machines = Machine.objects.filter(bk_host_id__in=all_machine_ids).select_related("bk_city")

    # 统计机器分布信息
    machine_distribution = {
        "total_count": len(all_machine_ids),
        "by_sub_zone": defaultdict(int),
        "by_os": defaultdict(int),
        "by_device_class": defaultdict(int),
        "spec_summary": defaultdict(int),
    }

    for machine in machines:
        # 子Zone分布
        if machine.bk_sub_zone:
            machine_distribution["by_sub_zone"][machine.bk_sub_zone] += 1

        # 操作系统分布
        if machine.bk_os_name:
            machine_distribution["by_os"][machine.bk_os_name] += 1

        # 设备类型分布
        if machine.bk_svr_device_cls_name:
            machine_distribution["by_device_class"][machine.bk_svr_device_cls_name] += 1

        # 规格统计
        if machine.spec_id:
            machine_distribution["spec_summary"][f"spec_{machine.spec_id}"] += 1

    return machine_distribution


def es_cluster_overview(immute_domain: str) -> Dict:
    cluster_obj = Cluster.objects.prefetch_related("tags").get(immute_domain=immute_domain)
    # 基本信息
    stats = {
        "bk_cloud_id": cluster_obj.bk_cloud_id,
        "bk_biz_id": cluster_obj.bk_biz_id,
        "cluster_id": cluster_obj.id,
        "immute_domain": cluster_obj.immute_domain,
        "alias": cluster_obj.alias,
        "cluster_type": cluster_obj.cluster_type,
        "major_version": cluster_obj.major_version,
        "region": cluster_obj.region,
        "disaster_tolerance_level": cluster_obj.disaster_tolerance_level,
        "tags": ["{}:{}".format(tag.key, tag.value) for tag in cluster_obj.tags.all()],
        "cluster_entries": [
            {"entry_type": ce.cluster_entry_type, "entry_addr": ce.entry}
            for ce in ClusterEntry.objects.filter(cluster=cluster_obj)
        ],
    }
    # 查询存储实例
    storage_instances = (
        StorageInstance.objects.filter(cluster=cluster_obj)
        .select_related("machine", "machine__bk_city")
        .prefetch_related("bind_entry")
    )

    # 统计存储实例信息
    storage_stats = {
        "by_role": defaultdict(int),
        "by_status": defaultdict(int),
        "by_machine_type": defaultdict(int),
        "versions": set(),
        "machines": set(),
    }

    for instance in storage_instances:
        storage_stats["by_role"][instance.instance_role] += 1
        storage_stats["by_status"][instance.status] += 1
        storage_stats["by_machine_type"][instance.machine_type] += 1
        if instance.version:
            storage_stats["versions"].add(instance.version)
        storage_stats["machines"].add(instance.machine.bk_host_id)

    storage_machines = get_machine_stats(storage_stats["machines"])
    # 转换为普通字典并排序
    stats["storage_instances"] = {
        "node_count": storage_instances.count(),
        "by_role": dict(sorted(storage_stats["by_role"].items())),
        "by_status": dict(sorted(storage_stats["by_status"].items())),
        "versions": sorted(list(storage_stats["versions"])),
        "machine_count": len(storage_stats["machines"]),
        "by_os": dict(sorted(storage_machines["by_os"].items())),
        "by_sub_zone": dict(sorted(storage_machines["by_sub_zone"].items())),
        "by_device_class": dict(sorted(storage_machines["by_device_class"].items())),
    }

    return stats


def list_es_nodes_by_role(immute_domain: str, role: str) -> List:
    c_obj = Cluster.objects.get(immute_domain=immute_domain)
    objs = c_obj.storageinstance_set.filter(instance_role=role)

    hosts, infos = {}, []
    for ins_obj in objs:
        if not hosts.get(ins_obj.machine.ip):
            hosts[ins_obj.machine.ip] = []
        hosts[ins_obj.machine.ip].append(ins_obj.port)

    for ip, ports in hosts.items():
        m_obj = Machine.objects.get(ip=ip, bk_cloud_id=c_obj.bk_cloud_id, bk_biz_id=c_obj.bk_biz_id)
        infos.append(
            {"ip": ip, "ports": ports, "sub_zone": m_obj.bk_sub_zone, "cls_name": m_obj.bk_svr_device_cls_name}
        )

    return infos


def list_es_master_nodes(immute_domain: str) -> List:
    """集群 master节点 列表"""
    return list_es_nodes_by_role(immute_domain, InstanceRole.ES_MASTER)


def list_es_client_nodes(immute_domain: str) -> List:
    """集群 client节点 列表"""
    return list_es_nodes_by_role(immute_domain, InstanceRole.ES_CLIENT)


def list_es_hot_nodes(immute_domain: str) -> List:
    """集群 热数据节点 列表"""
    return list_es_nodes_by_role(immute_domain, InstanceRole.ES_DATANODE_HOT)


def list_es_cold_nodes(immute_domain: str) -> List:
    """集群 冷数据节点 列表"""
    return list_es_nodes_by_role(immute_domain, InstanceRole.ES_DATANODE_COLD)


def list_es_clusters_by_hosts(hosts: List) -> List[Dict]:
    cluster_host = []

    # 通过storageinstance查询
    storage_data = (
        Cluster.objects.filter(storageinstance__machine__ip__in=hosts)
        .values(
            "immute_domain", host=F("storageinstance__machine__ip"), instance_role=F("storageinstance__instance_role")
        )
        .distinct()
    )

    cluster_host.extend(storage_data)

    # 去重（如果需要）
    seen = set()
    unique_results = []
    for item in cluster_host:
        key = (item["immute_domain"], item["host"], item["instance_role"])
        if key not in seen:
            seen.add(key)
            unique_results.append(item)

    return unique_results
