import unittest
from unittest.mock import patch, MagicMock
from flowsense.storage.garage import GarageStorageClient
from flowsense.storage.sync import FlowSenseSyncManager

class TestGarageStorageClient(unittest.TestCase):
    
    @patch("boto3.client")
    def setUp(self, mock_client):
        self.client = GarageStorageClient()
        self.client.s3_client = mock_client()
        
    def test_ensure_bucket(self):
        self.client.ensure_bucket()
        self.client.s3_client.head_bucket.assert_called_once_with(Bucket=self.client.bucket_name)
        
    def test_upload_file(self):
        self.client.upload_file("local.txt", "remote.txt")
        self.client.s3_client.upload_file.assert_called_once_with("local.txt", self.client.bucket_name, "remote.txt")

class TestFlowSenseSyncManager(unittest.TestCase):
    
    @patch("flowsense.storage.sync.GarageStorageClient")
    def test_sync_now(self, mock_garage_client):
        sync_manager = FlowSenseSyncManager()
        sync_manager.sync_detections = MagicMock()
        sync_manager.sync_models = MagicMock()
        sync_manager.sync_configs = MagicMock()
        
        sync_manager.sync_now()
        sync_manager.sync_detections.assert_called_once()
        sync_manager.sync_models.assert_called_once()
        sync_manager.sync_configs.assert_called_once()

if __name__ == "__main__":
    unittest.main()
