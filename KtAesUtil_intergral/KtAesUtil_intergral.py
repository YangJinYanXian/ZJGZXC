import base64
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

class KtAesUtilIntergral:
    @staticmethod
    def encrypt(content: str, password: str) -> str:
        try:
            # 生成16字节的密钥，不足补零，超过截断
            key = password.encode('utf-8').ljust(16, b'\0')[:16]
            cipher = AES.new(key, AES.MODE_ECB)
            padded_data = pad(content.encode('utf-8'), AES.block_size)
            encrypted_bytes = cipher.encrypt(padded_data)
            return base64.b64encode(encrypted_bytes).decode('utf-8')
        except Exception as e:
            raise RuntimeError(f"加密过程中发生错误: {e}") from e

    @staticmethod
    def decrypt(encrypted_content: str, password: str) -> str:
        try:
            key = password.encode('utf-8').ljust(16, b'\0')[:16]
            cipher = AES.new(key, AES.MODE_ECB)
            encrypted_data = base64.b64decode(encrypted_content)
            decrypted_bytes = cipher.decrypt(encrypted_data)
            unpadded_data = unpad(decrypted_bytes, AES.block_size)
            return unpadded_data.decode('utf-8')
        except Exception as e:
            raise RuntimeError(f"解密过程中发生错误: {e}") from e

def encrypt_data(data: dict, key: str) -> str:
    """加密字典数据为JSON字符串后加密"""
    try:
        json_str = json.dumps(data)
        encrypted_data = KtAesUtilIntergral.encrypt(json_str, key)
        return encrypted_data
    except Exception as e:
        raise APIError(f"加密失败: {str(e)}")

def decrypt_data(encrypted_data: str, key: str) -> dict:
    """解密数据并解析为字典"""
    try:
        decrypted_str = KtAesUtilIntergral.decrypt(encrypted_data, key)
        return json.loads(decrypted_str)
    except Exception as e:
        raise APIError(f"解密失败: {str(e)}")

# 示例自定义异常类，需根据实际情况定义
class APIError(Exception):
    pass

def test_encryption_decryption():
    test_key = "testkey123"  # 测试密钥
    test_data = {"user": "admin", "level": 5}

    try:
        # 加密
        encrypted = encrypt_data(test_data, test_key)
        print(f"加密后数据: {encrypted}")

        # 解密
        decrypted = decrypt_data(encrypted, test_key)
        print(f"解密后数据: {decrypted}")

        # 验证解密结果和原始数据一致
        assert decrypted == test_data, "解密数据与原始数据不一致！"

        print("测试通过：加密和解密功能正常。")

    except APIError as e:
        print(f"APIError 测试失败: {e}")
    except AssertionError as e:
        print(f"断言失败: {e}")
    except Exception as e:
        print(f"其他错误: {e}")

# 执行测试
test_encryption_decryption()
