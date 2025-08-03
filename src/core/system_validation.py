import psutil

def bytes_to_readable(size_in_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.2f} PB"

def get_disk_status():
    info = []
    partitions = psutil.disk_partitions()
    for partition in partitions:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_data = {
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "total": bytes_to_readable(usage.total),
                "used": bytes_to_readable(usage.used),
                "free": bytes_to_readable(usage.free),
                "percent": usage.percent
            }
            print(disk_data)
            info.append(disk_data)

            # Print disk info (existing behavior)
            #print(f"Disk: {disk_data['device']}  Mount: {disk_data['mountpoint']}")
           # print(f"  Total: {disk_data['total']}, Used: {disk_data['used']}, Free: {disk_data['free']}, Usage: {disk_data['percent']}%")
        except PermissionError:
            continue
    return info
