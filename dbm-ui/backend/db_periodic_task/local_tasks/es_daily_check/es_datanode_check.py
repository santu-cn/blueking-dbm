import logging
from collections import Counter

from configuration.models import DBAdministrator
from db_meta.enums import InstanceRole, MachineType
from db_meta.models import AppCache, Machine
from db_report.enums import ReportStateType
from db_report.models import EsDatanodeReport

from backend.configuration.constants import DBType
from backend.db_meta.models import Cluster

logger = logging.getLogger("celery")


def check_es_datanode():
    """
    检查ES 数据节点信息
    1. 热节点机架亲合度
    2. 热节点机房亲合度
    3. 冷节点机房亲合度
    4. 冷节点机房亲合度
    """
    clusters = Cluster.objects.filter(cluster_type=DBType.Es)
    for cluster in clusters:
        hot_machines = Machine.objects.filter(
            storageinstance__cluster=cluster,
            storageinstance__instance_role=InstanceRole.ES_DATANODE_HOT,
            machine_type=MachineType.ES_DATANODE,
        )
        hot_count = hot_machines.count()
        list_rack_id_hot = list(hot_machines.values_list("bk_rack_id", flat=True))
        counter_rack_hot = Counter(list_rack_id_hot)
        list_idc_id_hot = list(hot_machines.values_list("bk_idc_id", flat=True))
        counter_idc_hot = Counter(list_idc_id_hot)

        cold_machines = Machine.objects.filter(
            storageinstance__cluster=cluster,
            storageinstance__instance_role=InstanceRole.ES_DATANODE_COLD,
            machine_type=MachineType.ES_DATANODE,
        )
        cold_count = cold_machines.count()
        list_rack_id_cold = list(cold_machines.values_list("bk_rack_id", flat=True))
        counter_rack_cold = Counter(list_rack_id_cold)
        list_idc_id_cold = list(cold_machines.values_list("bk_idc_id", flat=True))
        counter_idc_cold = Counter(list_idc_id_cold)

        app = AppCache.objects.get(bk_biz_id=cluster.bk_biz_id).db_app_abbr
        es_dba = DBAdministrator().get_biz_db_type_admins(cluster.bk_biz_id, DBType.Es)

        state = ReportStateType.NORMAL
        msg = f"ES cluster has {hot_count} hot machines, {cold_count} cold machines"

        if max(counter_rack_hot.values()) > 1 or max(counter_rack_cold.values()) > 1:
            msg += f", hot rack affinity is {max(counter_rack_hot.values())}"
            msg += f", cold rack affinity is {max(counter_rack_cold.values())}"
            state = ReportStateType.NORMAL.WARNING
        elif max(counter_idc_hot.values()) > 1 or max(counter_idc_cold.values()) > 1:
            # 机房亲合度暂时不需要warning状态
            msg += f", hot idc affinity is {max(counter_idc_hot.values())}"
            msg += f", cold idc affinity is {max(counter_idc_cold.values())}"

        try:
            EsDatanodeReport.objects.create(
                bk_biz_id=cluster.bk_biz_id,
                bk_cloud_id=cluster.bk_cloud_id,
                state=state,
                idc_affinity_hot=max(counter_idc_hot.values()),
                rack_affinity_hot=max(counter_rack_hot.values()),
                idc_affinity_cold=max(counter_idc_cold.values()),
                rack_affinity_cold=max(counter_rack_cold.values()),
                msg=msg,
                domain=cluster.immute_domain,
                app=app,
                dba=es_dba,
            )
        except Exception as e:
            logger.error(f"Error occurred while inserting data: {e}")
            raise NotImplementedError("{}-{} insert data failed, msg:{}".format(cluster.immute_domain, state, msg))
