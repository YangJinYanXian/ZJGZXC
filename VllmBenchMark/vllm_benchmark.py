import time
import asyncio
import aiohttp
import numpy as np
from typing import List, Dict, Optional
import json
from datetime import datetime


class VLLMTester:
    def __init__(self, jsonl_path: str, stream: bool = False, api_key: str = None):
        self.api_url = "http://localhost:8088/v1/chat/completions"
        self.test_samples = self.load_test_samples(jsonl_path)
        self.stream = stream
        self.chunk_separator = b"\n\n"
        self.api_key = api_key
        self.total_requests = 0

    def get_headers(self) -> Dict:
        """构造包含认证信息的请求头"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def load_test_samples(self, jsonl_path: str, num_samples: int = 10) -> List[Dict]:
        samples = []
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= num_samples:
                    break
                samples.append(json.loads(line.strip()))
        return samples

    async def process_stream_response(self, response, start_time: float) -> Optional[Dict]:
        """处理流式响应并收集指标"""
        if response.status != 200:
            print(f"API请求失败 HTTP {response.status}")
            return None

        buffer = b""
        first_token_time = None
        response_text = ""

        try:
            async for chunk in response.content.iter_any():
                buffer += chunk
                while self.chunk_separator in buffer:
                    parts = buffer.split(self.chunk_separator, 1)
                    event_part, buffer = parts

                    if not event_part.startswith(b"data: "):
                        continue

                    try:
                        event_data = json.loads(event_part[len(b"data: "):])
                        delta = event_data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")

                        if content:
                            response_text += content
                            if first_token_time is None:
                                first_token_time = time.time()
                    except json.JSONDecodeError:
                        continue

            if first_token_time is None:
                return None

            return {
                "first_token_time": first_token_time,
                "end_time": time.time(),
                "response_text": response_text
            }
        except Exception as e:
            print(f"流处理错误: {str(e)}")
            return None

    async def single_inference(self, sample: Dict, session: aiohttp.ClientSession) -> Dict:
        messages = sample['messages']
        payload = {
            "model": "Qwen2-7B",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 512,
            "stream": self.stream
        }

        metrics = {
            "success": False,
            "first_token_latency": 0,
            "total_time": 0,
            "generation_time": 0,
            "input_length": sample['length'],
            "output_length": 0,
            "error": None
        }

        try:
            start_time = time.time()
            async with session.post(
                    self.api_url,
                    json=payload,
                    headers=self.get_headers()
            ) as response:
                if response.status != 200:
                    error_info = await response.text()
                    metrics["error"] = f"HTTP {response.status}: {error_info[:200]}"
                    return metrics

                if self.stream:
                    stream_result = await self.process_stream_response(response, start_time)
                    if not stream_result:
                        metrics["error"] = "流处理失败"
                        return metrics

                    metrics.update({
                        "success": True,
                        "first_token_latency": (stream_result["first_token_time"] - start_time) * 1000,
                        "total_time": (stream_result["end_time"] - start_time) * 1000,
                        "generation_time": (stream_result["end_time"] - stream_result["first_token_time"]) * 1000,
                        "output_length": len(stream_result["response_text"])
                    })
                else:
                    result = await response.json()
                    end_time = time.time()

                    metrics.update({
                        "success": True,
                        "first_token_latency": (end_time - start_time) * 1000,
                        "total_time": (end_time - start_time) * 1000,
                        "generation_time": 0,
                        "output_length": len(result["choices"][0]["message"]["content"])
                    })

        except Exception as e:
            metrics["error"] = str(e)

        return metrics

    async def run_concurrent_test(self, concurrent_num: int) -> Dict:
        connector = aiohttp.TCPConnector(limit=0)
        async with aiohttp.ClientSession(connector=connector) as session:
            all_tasks = []
            for sample in self.test_samples:
                for _ in range(concurrent_num):
                    all_tasks.append(self.single_inference(sample, session))

            results = await asyncio.gather(*all_tasks)
            valid_results = [r for r in results if r["success"]]
            self.total_requests = len(results)

            if not valid_results:
                error_samples = [r for r in results if r["error"]]
                top_errors = [e["error"] for e in error_samples[:3]]
                return {
                    "error": "所有请求都失败",
                    "top_errors": top_errors
                }

            return self.calculate_metrics(valid_results)

    def calculate_metrics(self, valid_results: List[Dict]) -> Dict:
        latency_values = [r["first_token_latency"] for r in valid_results]
        total_times = [r["total_time"] for r in valid_results]
        output_lens = [r["output_length"] for r in valid_results]

        total_duration = sum(total_times) / 1000
        total_tokens = sum(output_lens)

        return {
            "avg_first_token_latency": np.mean(latency_values),
            "p50_first_token_latency": np.percentile(latency_values, 50),
            "p95_first_token_latency": np.percentile(latency_values, 95),
            "avg_total_time": np.mean(total_times),
            "throughput": total_tokens / total_duration if total_duration > 0 else 0,
            "success_rate": (len(valid_results) / self.total_requests) * 100,
            "total_requests": self.total_requests,
            "success_requests": len(valid_results)
        }


async def main():
    jsonl_path = r"C:\Users\YANGXIAN\Desktop\vllmbenchmark\chinese_filtered_1k.jsonl"  # 修改为实际路径
    api_key = "EMPTY"  # 在此填入API密钥

    for stream_mode in [True, False]:
        tester = VLLMTester(jsonl_path, stream=stream_mode, api_key=api_key)
        print(f"\n测试模式: {'流式' if stream_mode else '非流式'}")

        concurrency_levels = [1, 2, 4, 8]
        for concurrency in concurrency_levels:
            print(f"\n当前并发数: {concurrency}")
            start_test = time.time()
            metrics = await tester.run_concurrent_test(concurrency)

            if "error" in metrics:
                print(f"测试失败: {metrics['error']}")
                print("典型错误示例:")
                for err in metrics.get("top_errors", []):
                    print(f"- {err}")
                continue

            print(f"测试耗时: {time.time() - start_test:.2f}s")
            print(f"成功请求: {metrics['success_requests']}/{metrics['total_requests']}")
            print(f"成功率: {metrics['success_rate']:.1f}%")
            print(f"首token延迟 (平均): {metrics['avg_first_token_latency']:.1f}ms")
            print(f"首token延迟 (P95): {metrics['p95_first_token_latency']:.1f}ms")
            print(f"平均总响应时间: {metrics['avg_total_time']:.1f}ms")
            print(f"系统总吞吐量: {metrics['throughput']:.1f} tokens/s")


if __name__ == "__main__":
    asyncio.run(main())