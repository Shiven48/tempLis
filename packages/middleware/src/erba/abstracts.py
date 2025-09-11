from abc import ABC, abstractmethod
from typing import List, Union
from hl7 import Field, Sequence
from erba.constants import ERBA_YAML_PATH


class Processor(ABC):
    """Abstract base processor for HL7 segments."""

    yaml_path = ERBA_YAML_PATH
    
    @abstractmethod
    def process_segment(self) -> tuple[List, bool]:
        """
        Process a single HL7 message type.
                
        Returns:
            A list of errors and a flag if there is any error or not.
        """
        pass

    @abstractmethod
    def parse(self) -> Union[List[dict], tuple[dict, dict]]:
        """
        Parses a single HL7 segment based on the config mapping.

        Returns:
            Processed result in a list of dictionary form.
        """
        pass

    @staticmethod
    def safe_get(segment: Sequence, index: Union[int, str], default='') -> Union[Field, List, str]:
        """
        Safely extract field from HL7 segment, handling nested lists.
        Returns raw value without string conversion for intermediate steps.
        """
        try:
            if isinstance(index, int):
                if len(segment) <= index:
                    return default
                value = segment[index]
            elif isinstance(index, str):
                if hasattr(segment, 'get'):
                    value = segment.get(index, default)
                elif hasattr(segment, '__getitem__'):
                    try:
                        value = segment[index]
                    except (KeyError, IndexError):
                        return default
                else:
                    return default
            else:
                return default

            return value if value is not None else default
            
        except (IndexError, TypeError, AttributeError, KeyError):
            return default