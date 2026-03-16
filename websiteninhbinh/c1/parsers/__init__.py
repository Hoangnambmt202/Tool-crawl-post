from .type5 import Type5Parser
from .type2 import Type2Parser
from .type10 import Type10Parser
from .type11 import Type11Parser
from .type_default import TypeDefaultParser
from .hanam import HanamParser
from .congkhai import CongKhaiParser
from .generic import GenericParser

# Order matters: Specific -> Generic
AVAILABLE_PARSERS = [
    Type5Parser(),
    Type10Parser(),
    Type11Parser(),
    Type2Parser(),
    TypeDefaultParser(),
    HanamParser(),
    CongKhaiParser(),
    GenericParser(),
]
