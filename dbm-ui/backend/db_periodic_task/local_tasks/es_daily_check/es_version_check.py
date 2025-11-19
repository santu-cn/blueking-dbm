import logging
from collections import Counter

from configuration.models import DBAdministrator
from db_meta.models import AppCache, StorageInstance
from db_report.enums import ReportStateType
from db_report.models.es_version_report import EsVersionReport

from backend.configuration.constants import DBType
from backend.db_meta.models import Cluster

logger = logging.getLogger("celery")


def check_es_version():
    """
    检查ES 节点版本与cluster表版本一致性
    """
    clusters = Cluster.objects.filter(cluster_type=DBType.Es)
    for cluster in clusters:
        storage_instances = StorageInstance.objects.filter(cluster=cluster)
        list_version = [instance.version for instance in storage_instances]
        counter_version = Counter(list_version)
        versions = counter_version.keys()
        app = AppCache.objects.get(bk_biz_id=cluster.bk_biz_id).db_app_abbr
        es_dba = DBAdministrator().get_biz_db_type_admins(cluster.bk_biz_id, DBType.Es)
        state = ReportStateType.NORMAL
        msg = f"ES cluster major version is {cluster.major_version}"

        if len(versions) > 1 or cluster.major_version not in versions:
            state = ReportStateType.ABNORMAL
            msg += f", nodes has {len(versions)} versions, {str(counter_version)}"

        try:
            EsVersionReport.objects.create(
                bk_biz_id=cluster.bk_biz_id,
                bk_cloud_id=cluster.bk_cloud_id,
                state=state,
                msg=msg,
                domain=cluster.immute_domain,
                app=app,
                dba=es_dba,
                major_version=cluster.major_version,
                version_count=len(versions),
            )
        except Exception as e:
            logger.error(f"Error occurred while inserting data: {e}")
            raise NotImplementedError("{}-{} insert data failed, msg:{}".format(cluster.immute_domain, state, msg))
