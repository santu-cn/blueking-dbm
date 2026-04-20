"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import logging.config

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.es.impl.cluster_meta import (
    es_cluster_overview,
    list_es_biz_by_name,
    list_es_client_nodes,
    list_es_clusters,
    list_es_clusters_by_hosts,
    list_es_cold_nodes,
    list_es_hot_nodes,
    list_es_master_nodes,
    list_my_es_bizs,
)
from backend.dbm_aiagent.mcp_tools.es.serializers.cluster_meta import (
    EsBizDetailSerializer,
    EsBizInputSerializer,
    EsBizNameInputSerializer,
    EsClustersOutputSerializer,
    EsEmptyInputSerializer,
    EsHostClusterOutputSerializer,
    EsHostInputSerializer,
    EsInstancesSummarySerializer,
    EsTopoInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission

logger = logging.getLogger("flow")

"""
meta 相关的query
"""


class EsClusterTopoOutputSerializer:
    pass


class EsQueryMetaMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("查询我负责的ES业务列表")),
        request_slz=EsEmptyInputSerializer,
        response_slz=EsBizDetailSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ES_QUERY_META],
        name_prefix="es_query_meta",
    )
    def list_my_bizs(self, request, *args, **kwargs):
        return Response(list_my_es_bizs(userID=request.user.username))

    @mcp_tools_api_decorator(
        description=str(_("根据业务英文名查询业务详情")),
        request_slz=EsBizNameInputSerializer,
        response_slz=EsBizDetailSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ES_QUERY_META],
        name_prefix="es_query_meta",
    )
    def list_bizs_by_name(self, request, *args, **kwargs):
        biz_name = self.get_param("biz_name")

        return Response(list_es_biz_by_name(biz_name=biz_name))

    @mcp_tools_api_decorator(
        description=str(_("查询业务下的ES集群列表")),
        request_slz=EsBizInputSerializer,
        response_slz=EsClustersOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ES_QUERY_META],
        name_prefix="es_query_meta",
    )
    def list_es_clusters(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")

        return Response(list_es_clusters(bk_biz_id=bk_biz_id))

    @mcp_tools_api_decorator(
        description=str(
            _(
                """
查询指定集群的拓扑部署信息，包括集群基本信息、存储实例统计、代理实例统计、机器分布情况等详细信息
## 适用场景

1. **容量规划**: 查看集群节点数、机器数，评估资源使用情况
2. **容灾分析**: 查看子Zone分布，评估容灾能力
3. **版本管理**: 查看实例版本分布，规划升级计划
4. **故障排查**: 查看节点状态分布，快速定位异常节点
5. **成本分析**: 查看设备规格分布，评估资源成本

## 错误处理
- 如果集群不存在，返回错误信息：`{"error": "集群不存在"}`

## 结果展示
1. 存储层和接入层: 全部信息要融合成多行多列并且用一个表格展示
2. 基础信息部分: 采用分层结构化展示方式
"""
            )
        ),
        request_slz=EsTopoInputSerializer,
        response_slz=EsClusterTopoOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ES_QUERY_META],
        name_prefix="es_query_meta",
    )
    def cluster_overview(self, request, *args, **kwargs):
        immute_domain = self.get_param("immute_domain")
        return Response(es_cluster_overview(immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询 ES 集群的Client节点信息")),
        request_slz=EsTopoInputSerializer,
        response_slz=EsInstancesSummarySerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ES_QUERY_META],
        name_prefix="es_query_meta",
    )
    def list_cluster_client_nodes(self, request, *args, **kwargs):
        immute_domain = self.get_param("immute_domain")
        return Response(list_es_client_nodes(immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询 ES 集群的Master节点信息")),
        request_slz=EsTopoInputSerializer,
        response_slz=EsInstancesSummarySerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ES_QUERY_META],
        name_prefix="es_query_meta",
    )
    def list_cluster_masters(self, request, *args, **kwargs):
        immute_domain = self.get_param("immute_domain")
        return Response(list_es_master_nodes(immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询 ES 集群的热数据节点信息")),
        request_slz=EsTopoInputSerializer,
        response_slz=EsInstancesSummarySerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ES_QUERY_META],
        name_prefix="es_query_meta",
    )
    def list_cluster_hot_nodes(self, request, *args, **kwargs):
        immute_domain = self.get_param("immute_domain")
        return Response(list_es_hot_nodes(immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询 ES 集群的冷数据节点信息")),
        request_slz=EsTopoInputSerializer,
        response_slz=EsInstancesSummarySerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ES_QUERY_META],
        name_prefix="es_query_meta",
    )
    def list_cluster_cold_nodes(self, request, *args, **kwargs):
        immute_domain = self.get_param("immute_domain")
        return Response(list_es_cold_nodes(immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("根据输入的IP列表;查询ES集群列表")),
        request_slz=EsHostInputSerializer,
        response_slz=EsHostClusterOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ES_QUERY_META],
        name_prefix="es_query_meta",
    )
    def list_clusters_by_hosts(self, request, *args, **kwargs):
        hosts = self.get_param("hosts")
        return Response(list_es_clusters_by_hosts(hosts=hosts))
