from shortuuid.main import ShortUUID
from shortuuid.main import int_to_string
from shortuuid.main import string_to_int


class ShortUUIDExtended(ShortUUID):
    def encodex(self, data: bytes | str, pad_length: int | None = None) -> str:
        """
        Convert bytes to b57-encoded string
        """
        if not isinstance(data, (str, bytes)):
            msg = "Input `data` must be bytes or str."
            raise ValueError(msg)
        if isinstance(data, str):
            data = data.encode("utf-8")
        number = int.from_bytes(data, byteorder="big")
        if pad_length is None:
            pad_length = self._length
        return int_to_string(number, self._alphabet, padding=pad_length)

    def decodex(self, data: bytes | str) -> bytes:
        """
        Converts b57-encoded string to bytes
        """
        if not isinstance(data, (str, bytes)):
            msg = "Input `data` must be bytes or str."
            raise ValueError(msg)
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        number = string_to_int(data, self._alphabet)
        num_bytes = (number.bit_length() + 7) // 8
        return number.to_bytes(num_bytes, byteorder="big")


# For backwards compatibility with the extended class
_extended_instance = ShortUUIDExtended()
encodex = _extended_instance.encodex
decodex = _extended_instance.decodex
uuid = _extended_instance.uuid
encode = _extended_instance.encode
decode = _extended_instance.decode
random = _extended_instance.random
get_alphabet = _extended_instance.get_alphabet
set_alphabet = _extended_instance.set_alphabet


__all__ = [
    "ShortUUIDExtended",
    "encodex",
    "decodex",
    "uuid",
    "encode",
    "decode",
    "random",
    "get_alphabet",
    "set_alphabet",
]
