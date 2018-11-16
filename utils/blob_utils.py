from azure.storage.blob import BlockBlobService, ContentSettings

class BlobStorage():
    azure_storage_client = None
    
    #TODO: Verify the storage account is correct. Currently we get an unhelpful error message if you have a type in Storage Name
    @staticmethod
    def get_azure_storage_client(config):
        if BlobStorage.azure_storage_client is not None:
            return BlobStorage.azure_storage_client

        BlobStorage.azure_storage_client = BlockBlobService(
            config.get("storage_account"),
            account_key=config.get("storage_key")
        )

        return BlobStorage.azure_storage_client