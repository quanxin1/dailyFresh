from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client
from django.conf import settings
class FDSStorage(Storage):
    """文件存储"""
    def __init__(self,client_conf=None,base_url=None):
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf

        if base_url is None:
            base_url = settings.FDFS_URL
        self.base_url = base_url

    def _open(self,name,mode='rb'):
        """打开文件时使用"""
        pass
    def _save(self,name,content):
        """保存文件时使用"""
        client=Fdfs_client(self.client_conf)
        ret=client.upload_by_buffer(content.read())
        if ret.get('Status') !='Upload successed.':
            raise Exception('上传文件失败')
        file_name=ret.get('Remote file_id')
        return file_name
    def exists(self, name):
        """Django 判断文件名是否存在"""
        return False
    def url(self, name):
        return self.base_url+name
