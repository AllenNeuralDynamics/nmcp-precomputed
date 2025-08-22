import pytest
from unittest.mock import Mock, patch
from nmcp.data.remote_data_client import RemoteDataClient


class TestRemoteDataClient:
    
    @pytest.fixture
    def mock_client(self):
        with patch("nmcp.data.remote_data_client.Client") as mock_client_class:
            mock_client_instance = Mock()
            mock_client_class.return_value = mock_client_instance
            
            client = RemoteDataClient("http://test-url.com", "test-auth-key")
            client._client = mock_client_instance
            return client, mock_client_instance

    def test_get_reconstruction_header_success(self, mock_client):
        client, mock_gql_client = mock_client
        
        # Mock the GraphQL response
        mock_response = {
            "reconstructionDataChunked": {
                "header": {
                    "id": "test-id",
                    "idString": "test-id-string", 
                    "DOI": "test-doi",
                    "soma": {
                        "x": 1.0,
                        "y": 2.0,
                        "z": 3.0
                    }
                },
                "allenInformation": [{"allenId": 1, "name": "test"}]
            }
        }
        mock_gql_client.execute.return_value = mock_response
        
        # Call the method
        result = client.get_reconstruction_header("test-reconstruction-id")
        
        # Verify the result
        expected = {
            "id": "test-id",
            "idString": "test-id-string",
            "DOI": "test-doi",
            "allenInformation": [{"allenId": 1, "name": "test"}],
            "soma": {"x": 1.0, "y": 2.0, "z": 3.0}
        }
        assert result == expected
        
        # Verify the GraphQL call
        mock_gql_client.execute.assert_called_once()
        call_args = mock_gql_client.execute.call_args
        assert call_args[1]["variable_values"]["id"] == "test-reconstruction-id"
        assert call_args[1]["variable_values"]["input"]["parts"] == ["header", "allenInformation"]

    def test_get_reconstruction_header_no_soma(self, mock_client):
        client, mock_gql_client = mock_client
        
        # Mock response without soma
        mock_response = {
            "reconstructionDataChunked": {
                "header": {
                    "id": "test-id",
                    "idString": "test-id-string",
                    "DOI": "test-doi",
                    "soma": None
                },
                "allenInformation": []
            }
        }
        mock_gql_client.execute.return_value = mock_response
        
        result = client.get_reconstruction_header("test-reconstruction-id")
        
        assert "soma" not in result
        assert result["allenInformation"] == []

    def test_get_reconstruction_header_failure(self, mock_client):
        client, mock_gql_client = mock_client
        
        # Mock empty response
        mock_gql_client.execute.return_value = None
        
        result = client.get_reconstruction_header("test-reconstruction-id")
        
        assert result is None

    def test_get_axon_chunks_success(self, mock_client):
        client, mock_gql_client = mock_client
        
        # Mock response with axon data
        mock_response = {
            "reconstructionDataChunked": {
                "axon": [
                    {"x": 1.0, "y": 2.0, "z": 3.0, "radius": 0.5, "sampleNumber": 1},
                    {"x": 2.0, "y": 3.0, "z": 4.0, "radius": 0.6, "sampleNumber": 2}
                ],
                "axonChunkInfo": {
                    "totalCount": 2,
                    "offset": 0,
                    "limit": 10000,
                    "hasMore": False
                }
            }
        }
        mock_gql_client.execute.return_value = mock_response
        
        result = client.get_axon_chunks("test-reconstruction-id", chunk_size=5000)
        
        assert result is not None
        assert len(result["data"]) == 2
        assert result["data"][0]["x"] == 1.0
        assert result["chunk_info"]["total_retrieved"] == 2
        assert result["chunk_info"]["offset"] == 0
        assert result["chunk_info"]["requested_limit"] is None

    def test_get_axon_chunks_with_limit(self, mock_client):
        client, mock_gql_client = mock_client
        
        # Mock response with limited data
        mock_response = {
            "reconstructionDataChunked": {
                "axon": [{"x": 1.0, "y": 2.0, "z": 3.0, "radius": 0.5, "sampleNumber": 1}],
                "axonChunkInfo": {
                    "totalCount": 1,
                    "offset": 10,
                    "limit": 1,
                    "hasMore": False
                }
            }
        }
        mock_gql_client.execute.return_value = mock_response
        
        result = client.get_axon_chunks("test-reconstruction-id", offset=10, limit=1)
        
        assert result is not None
        assert len(result["data"]) == 1
        assert result["chunk_info"]["offset"] == 10
        assert result["chunk_info"]["requested_limit"] == 1

    def test_get_dendrite_chunks_success(self, mock_client):
        client, mock_gql_client = mock_client
        
        # Mock response with dendrite data
        mock_response = {
            "reconstructionDataChunked": {
                "dendrite": [
                    {"x": 5.0, "y": 6.0, "z": 7.0, "radius": 0.3, "sampleNumber": 1},
                    {"x": 6.0, "y": 7.0, "z": 8.0, "radius": 0.4, "sampleNumber": 2}
                ],
                "dendriteChunkInfo": {
                    "totalCount": 2,
                    "offset": 0,
                    "limit": 10000,
                    "hasMore": False
                }
            }
        }
        mock_gql_client.execute.return_value = mock_response
        
        result = client.get_dendrite_chunks("test-reconstruction-id")
        
        assert result is not None
        assert len(result["data"]) == 2
        assert result["data"][0]["x"] == 5.0
        assert result["chunk_info"]["total_retrieved"] == 2

    def test_get_reconstruction_data_success(self, mock_client):
        client, mock_gql_client = mock_client
        
        # Mock the individual methods instead of the GraphQL client
        with patch.object(client, "get_reconstruction_header") as mock_header, \
             patch.object(client, "get_axon_chunks") as mock_axon, \
             patch.object(client, "get_dendrite_chunks") as mock_dendrite:
            
            # Set up mock returns
            mock_header.return_value = {
                "id": "test-id",
                "idString": "test-id-string",
                "DOI": "test-doi",
                "allenInformation": [],
                "soma": {"x": 1.0, "y": 2.0, "z": 3.0}
            }
            
            mock_axon.return_value = {
                "data": [{"x": 10.0, "y": 11.0, "z": 12.0}],
                "chunk_info": {"total_retrieved": 1}
            }
            
            mock_dendrite.return_value = {
                "data": [{"x": 20.0, "y": 21.0, "z": 22.0}],
                "chunk_info": {"total_retrieved": 1}
            }
            
            # Call the method
            result = client.get_reconstruction_data("test-reconstruction-id")
            
            # Verify the result structure
            assert result is not None
            assert result["id"] == "test-id"
            assert result["idString"] == "test-id-string"
            assert result["DOI"] == "test-doi"
            assert result["soma"] == {"x": 1.0, "y": 2.0, "z": 3.0}
            assert len(result["axon"]) == 1
            assert len(result["dendrite"]) == 1
            assert result["axon"][0]["x"] == 10.0
            assert result["dendrite"][0]["x"] == 20.0
            
            # Verify all methods were called
            mock_header.assert_called_once_with("test-reconstruction-id")
            mock_axon.assert_called_once_with("test-reconstruction-id")
            mock_dendrite.assert_called_once_with("test-reconstruction-id")

    def test_get_reconstruction_data_header_failure(self, mock_client):
        client, mock_gql_client = mock_client
        
        with patch.object(client, "get_reconstruction_header") as mock_header:
            mock_header.return_value = None
            
            result = client.get_reconstruction_data("test-reconstruction-id")
            
            assert result is None

    def test_get_reconstruction_data_no_soma(self, mock_client):
        client, mock_gql_client = mock_client
        
        with patch.object(client, "get_reconstruction_header") as mock_header, \
             patch.object(client, "get_axon_chunks") as mock_axon, \
             patch.object(client, "get_dendrite_chunks") as mock_dendrite:
            
            # Header without soma
            mock_header.return_value = {
                "id": "test-id",
                "idString": "test-id-string",
                "DOI": "test-doi",
                "allenInformation": []
            }
            
            mock_axon.return_value = {"data": [], "chunk_info": {}}
            mock_dendrite.return_value = {"data": [], "chunk_info": {}}
            
            result = client.get_reconstruction_data("test-reconstruction-id")
            
            assert "soma" not in result
            assert result["axon"] == []
            assert result["dendrite"] == []