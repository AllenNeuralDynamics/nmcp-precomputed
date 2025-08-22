import json
import logging
from datetime import datetime
from typing import List

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from .precomputed_entry import PrecomputedEntry

logger = logging.getLogger(__name__)

pending_query = gql(
    """
    query QueryPrecomputed {
          pendingPrecomputed {
            id
            skeletonSegmentId
            version
            generatedAt
            reconstructionId
          }
    }
    """
)

update_mutation = gql(
    """
    mutation UpdatePrecomputed($id: String!, $version: Int!, $generatedAt: Date!) {
        updatePrecomputed(id: $id, version: $version, generatedAt: $generatedAt) {
            id
            skeletonSegmentId
            version
            generatedAt
            reconstructionId
        }
    }
    """
)

reconstruction_data_query = gql(
    """
    query ReconstructionData($id: String!, $input: ReconstructionDataChunkedInput) {
        reconstructionDataChunked(id: $id, input: $input) {
            header {
                id
                idString
                DOI
                soma {
                    x
                    y
                    z
                    allenId
                }
                sample {
                    genotype
                }
            }
            axon {
                x
                y
                z
                radius
                sampleNumber
                parentNumber
                allenId
                structureIdentifier
            }
            axonChunkInfo {
                totalCount
                offset
                limit
                hasMore
            }
            dendrite {
                x
                y
                z
                radius
                sampleNumber
                parentNumber
                allenId
                structureIdentifier
            }
            dendriteChunkInfo {
                totalCount
                offset
                limit
                hasMore
            }
        }
    }
    """
)


class RemoteDataClient:
    def __init__(self, url: str, auth_key: str):
        transport = RequestsHTTPTransport(
            url=url,
            verify=True,
            retries=3,
            headers={"Content-Type": "application/json", "Authorization": auth_key}
        )

        self._client = Client(transport=transport, fetch_schema_from_transport=False)

    def find_pending(self) -> List[PrecomputedEntry]:
        pending = list()

        result = self._client.execute(pending_query)

        for precomputed in result["pendingPrecomputed"]:
            pending.append(PrecomputedEntry(**precomputed))

        return pending

    def mark_generated(self, entry_id: str) -> None:
        params = {"id": entry_id, "version": 1, "generatedAt": datetime.now().timestamp() * 1000}
        result = self._client.execute(update_mutation, variable_values=params)

    def mark_failed(self, entry_id: str) -> None:
        params = {"id": entry_id, "version": -1, "generatedAt": datetime.now().timestamp() * 1000}
        result = self._client.execute(update_mutation, variable_values=params)

    def get_reconstruction_header(self, reconstruction_id: str):
        """Get header information for a reconstruction."""
        try:
            header_input = {
                "parts": ["header"]
            }
            params = {"id": reconstruction_id, "input": header_input}
            result = self._client.execute(reconstruction_data_query, variable_values=params)
            
            if not result or "reconstructionDataChunked" not in result:
                return None
            
            data = result["reconstructionDataChunked"]
            
            return data["header"]

        except Exception as ex:
            logger.error(f"Error getting reconstruction header for {reconstruction_id}: {ex}")

        return None

    def get_axon_chunks(self, reconstruction_id: str, chunk_size: int = 25000, offset: int = 0, limit: int = None):
        """Get axon data in chunks for a reconstruction.
        
        Args:
            reconstruction_id: The ID of the reconstruction
            chunk_size: Number of points to retrieve per request
            offset: Starting offset for retrieval
            limit: Maximum total number of points to retrieve (None for all)
        
        Returns:
            Dict with "data" (list of axon points) and "chunk_info" (pagination info)
        """
        try:
            axon_data = []
            current_offset = offset
            remaining_limit = limit
            
            while True:
                # Calculate limit for this chunk
                request_limit = chunk_size
                if remaining_limit is not None:
                    request_limit = min(chunk_size, remaining_limit)
                    if request_limit <= 0:
                        break
                
                axon_input = {
                    "parts": ["axon"],
                    "axonOffset": current_offset,
                    "axonLimit": request_limit
                }
                params = {"id": reconstruction_id, "input": axon_input}
                result = self._client.execute(reconstruction_data_query, variable_values=params)
                
                if result and "reconstructionDataChunked" in result:
                    chunk_data = result["reconstructionDataChunked"]
                    chunk_points = chunk_data["axon"] or []
                    axon_data.extend(chunk_points)
                    
                    # Update tracking variables
                    if remaining_limit is not None:
                        remaining_limit -= len(chunk_points)
                    current_offset += len(chunk_points)
                    
                    # Check if we have more data and should continue
                    chunk_info = chunk_data["axonChunkInfo"]
                    if not chunk_info or not chunk_info["hasMore"] or len(chunk_points) == 0:
                        break
                        
                    # If we got fewer points than requested, we"re done
                    if len(chunk_points) < request_limit:
                        break
                else:
                    break
            
            return {
                "data": axon_data,
                "chunk_info": {
                    "total_retrieved": len(axon_data),
                    "offset": offset,
                    "requested_limit": limit
                }
            }

        except Exception as ex:
            logger.error(f"Error getting axon chunks for {reconstruction_id}: {ex}")

        return None

    def get_dendrite_chunks(self, reconstruction_id: str, chunk_size: int = 25000, offset: int = 0, limit: int = None):
        """Get dendrite data in chunks for a reconstruction.
        
        Args:
            reconstruction_id: The ID of the reconstruction
            chunk_size: Number of points to retrieve per request
            offset: Starting offset for retrieval
            limit: Maximum total number of points to retrieve (None for all)
        
        Returns:
            Dict with "data" (list of dendrite points) and "chunk_info" (pagination info)
        """
        try:
            dendrite_data = []
            current_offset = offset
            remaining_limit = limit
            
            while True:
                # Calculate limit for this chunk
                request_limit = chunk_size
                if remaining_limit is not None:
                    request_limit = min(chunk_size, remaining_limit)
                    if request_limit <= 0:
                        break
                
                dendrite_input = {
                    "parts": ["dendrite"],
                    "dendriteOffset": current_offset,
                    "dendriteLimit": request_limit
                }
                params = {"id": reconstruction_id, "input": dendrite_input}
                result = self._client.execute(reconstruction_data_query, variable_values=params)
                
                if result and "reconstructionDataChunked" in result:
                    chunk_data = result["reconstructionDataChunked"]
                    chunk_points = chunk_data["dendrite"] or []
                    dendrite_data.extend(chunk_points)
                    
                    # Update tracking variables
                    if remaining_limit is not None:
                        remaining_limit -= len(chunk_points)
                    current_offset += len(chunk_points)
                    
                    # Check if we have more data and should continue
                    chunk_info = chunk_data["dendriteChunkInfo"]
                    if not chunk_info or not chunk_info["hasMore"] or len(chunk_points) == 0:
                        break
                        
                    # If we got fewer points than requested, we"re done
                    if len(chunk_points) < request_limit:
                        break
                else:
                    break
            
            return {
                "data": dendrite_data,
                "chunk_info": {
                    "total_retrieved": len(dendrite_data),
                    "offset": offset,
                    "requested_limit": limit
                }
            }

        except Exception as ex:
            logger.error(f"Error getting dendrite chunks for {reconstruction_id}: {ex}")

        return None

    def get_reconstruction_data(self, reconstruction_id: str):
        """Get complete reconstruction data using the individual chunk methods.
        
        Maintains backward compatibility with the original interface.
        """
        try:
            # Get header data
            header = self.get_reconstruction_header(reconstruction_id)
            if not header:
                return None
            
            # Build neuron object from header data
            neuron = {
                "id": header["id"],
                "idString": header["idString"],
                "DOI": header["DOI"],
                "allenInformation": header["allenInformation"],
                "axon": [],
                "dendrite": []
            }
            
            # Include soma if present
            if "soma" in header:
                neuron["soma"] = header["soma"]
            
            # Get all axon data
            axon_result = self.get_axon_chunks(reconstruction_id)
            if axon_result and axon_result["data"]:
                neuron["axon"] = axon_result["data"]
            
            # Get all dendrite data
            dendrite_result = self.get_dendrite_chunks(reconstruction_id)
            if dendrite_result and dendrite_result["data"]:
                neuron["dendrite"] = dendrite_result["data"]
            
            return neuron

        except Exception as ex:
            logger.error(f"Error getting reconstruction data for {reconstruction_id}: {ex}")

        return None
