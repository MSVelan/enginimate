#!/usr/bin/env python3
"""
Test script for the LLM API
Usage: python test_api.py <your-space-url>
"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

bearer_token = os.getenv("HF_TOKEN")

headers = {
    "Authorization": f"Bearer {bearer_token}",
    "Content-Type": "application/json",  # Optional: Add other headers as needed
}


def test_models(base_url):
    """Test models endpoint"""
    try:
        response = requests.get(f"{base_url}/v1/models", headers=headers)
        print(f"✓ Models endpoint: {response.status_code}")
        if response.status_code == 200:
            models = response.json()
            print(f"  Available models: {json.dumps(models, indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Models endpoint failed: {e}")
        return False


def test_completion(base_url):
    """Test completion endpoint"""
    payload = {
        "stream": True,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful bot, write python program for the given query. \
DO NOT include any additional statements/comments other than code.",
            },
            {
                "role": "user",
                "content": """
You are given an integer array nums.
You must replace exactly one element in the array with any integer value in the range [-10^5, 10^5] (inclusive).
After performing this single replacement, determine the maximum possible product of any three elements at distinct indices from the modified array.
Return an integer denoting the maximum product achievable.
Example 1:
Input: nums = [-5,7,0]
Output: 3500000
Explanation:
Replacing 0 with -10^5 gives the array [-5, 7, -10^5], which has a product (-5) * 7 * (-10^5) = 3500000. The maximum product is 3500000.

Example 2:
Input: nums = [-4,-2,-1,-3]
Output: 1200000
Explanation:
Two ways to achieve the maximum product include:
    [-4, -2, -3] → replace -2 with 10^5 → product = (-4) * 10^5 * (-3) = 1200000.
    [-4, -1, -3] → replace -1 with 10^5 → product = (-4) * 10^5 * (-3) = 1200000.
The maximum product is 1200000.

Fill out the following function:

class Solution:
    def maxProduct(self, nums: List[int]) -> int:
        pass
""",
            },
        ],
    }

    try:
        print(f"\nTesting completion with payload:")
        print(json.dumps(payload, indent=2))

        response = requests.post(
            f"{base_url}/v1/chat/completions", json=payload, headers=headers
        )

        print(f"\nResponse status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response body: {response.text[:500]}")

        if response.status_code == 200:
            result = response.json()
            print(f"\n✓ Completion successful!")
            print(f"Response: {result['choices'][0]['message']['content']}")
            return True
        else:
            print(f"\n✗ Completion failed with status {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Completion request failed: {e}")
        return False


def main():
    base_url = "https://msvelan-coding-llm.hf.space"

    print(f"Testing LLM API at: {base_url}\n")
    print("=" * 50)

    # Run tests
    # test_models(base_url)
    # print()
    test_completion(base_url)


if __name__ == "__main__":
    main()
