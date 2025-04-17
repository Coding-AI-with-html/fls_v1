import json
import os

class Device:
    def __init__(self, info, product_name="CIFX 70E-DP"):
        self.info = info
        self.product_name = product_name

    def __repr__(self):
        return repr(self.info)

    def __str__(self):
        details = self.info.get(self.product_name)
        if not details:
            return f"{self.product_name}: Product not found"
        return "\n".join(details)

def load_device_data(path="devices.json"):
    with open(path, "r") as f:
        return json.load(f)

# Optional CLI

def main():
    print("Current working directory:", os.getcwd())
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", default="CIFX 70E-DP")
    parser.add_argument("--data", default="devices.json")
    args = parser.parse_args()

    info = load_device_data(args.data)
    device = Device(info, args.product)
    print(repr(device))  # raw data
    print(str(device))   # clean output


if __name__ == "__main__":
    main