from .compression import compress_data, decompress_data
from .method1_xy import encode as method1_encode, decode as method1_decode
from .method2_raw_groups import encode as method2_encode, decode as method2_decode
from .method3_base10000 import encode as method3_encode, decode as method3_decode
from .method4_base64_groups import encode as method4_encode, decode as method4_decode
from .method5_property31 import encode as method5_encode, decode as method5_decode
from .method6_optimized import encode as method6_encode, decode as method6_decode

METHODS = {
    1: (method1_encode, method1_decode, "X/Y Coordinates - Unoptimized"),
    2: (method2_encode, method2_decode, "Raw Groups - 1GB levels"),
    3: (method3_encode, method3_decode, "Base 10000 - Slow"),
    4: (method4_encode, method4_decode, "Base64 Groups - Stripped by GD"),
    5: (method5_encode, method5_decode, "Property 31 - Doesn't work"),
    6: (method6_encode, method6_decode, "Optimized Base 9999 - Best"),
}

DEFAULT_METHOD = 6
