from storages.backends.gcloud import GoogleCloudStorage
from django.conf import settings

# Storage para arquivos privados no GCS


class PrivateMediaStorage(GoogleCloudStorage):
    # Nome do bucket (definido no settings)
    bucket_name = settings.GS_BUCKET_NAME    
    file_overwrite = False  # Não sobrescreve arquivos com mesmo nome
    # default_acl = 'private'  # Arquivos não são públicos
