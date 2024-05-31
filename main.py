import asyncio
import argparse
import httpx
import tldextract
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from typing import List


@retry(stop=stop_after_attempt(5), wait=wait_fixed(3), retry=(retry_if_exception_type(Exception)))
async def fetch_subdomains(domain_to_fetch: str) -> List[str]:
    url = f"https://crt.sh/?q={domain_to_fetch}&output=json"
    async with httpx.AsyncClient() as client:
        try:
            timeout = httpx.Timeout(timeout=30.0, read=None) # Sometimes crt.sh is slow, so wait 30 sec.
            response = await client.get(url, timeout=timeout)
            if "application/json" not in response.headers.get("content-type", ""):
                raise ValueError("Response is not in JSON format")

            data = response.json()
            subdomains = []
            for item in data:
                subdomains_value = item.get("name_value")
                if subdomains_value:
                    if "\n" not in subdomains_value:
                        if subdomains_value not in subdomains:
                            if tldextract.extract(subdomains_value).subdomain and "*" not in subdomains_value:
                                subdomains.append(subdomains_value)
                    else:
                        for i in subdomains_value.split("\n"):
                            if i not in subdomains:
                                if tldextract.extract(i).subdomain and "*" not in i:
                                    subdomains.append(i)

            return subdomains

        except Exception as e:
            print(f"It seems like crt.sh is down, try again later. Error: {e}")
            raise  # Reraise the exception to trigger a retry attempt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch subdomains for a given domain.")
    parser.add_argument('domain', type=str, help='The domain to fetch subdomains for.')

    args = parser.parse_args()

    domain = args.domain
    results = asyncio.run(fetch_subdomains(domain_to_fetch=domain))
    print("\n".join(results))
