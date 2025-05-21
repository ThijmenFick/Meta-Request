from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__)
file_path = "offenders.txt"

def get_current_timestamp():
    now = datetime.now()
    return now.strftime("%Y:%m:%d:%H:%M")

def parse_timestamp(ts_str):
    return datetime.strptime(ts_str, "%Y:%m:%d:%H:%M")

def update_offenders(file_path, encrypted_name, status):
    status = status.lower()
    if status not in ["active", "passive"]:
        raise ValueError("Status must be either 'active' or 'passive'")

    last_seen = get_current_timestamp()

    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []

    updated = False
    new_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split("!")]
        name = parts[0]
        if name == encrypted_name:
            new_lines.append(f"{encrypted_name} ! {status} ! {last_seen}\n")
            updated = True
        else:
            existing_status = parts[1] if len(parts) > 1 else "unknown"
            existing_seen = parts[2] if len(parts) > 2 else "unknown"
            new_lines.append(f"{name} ! {existing_status} ! {existing_seen}\n")

    if not updated:
        new_lines.append(f"{encrypted_name} ! {status} ! {last_seen}\n")

    with open(file_path, 'w') as f:
        f.writelines(new_lines)

    return "Updated" if updated else "Added"

@app.route("/register_offender")
def register_offender():
    encrypted_name = request.args.get('encrypted_name')
    status = request.args.get('status')

    if not encrypted_name or not status:
        return jsonify({"error": "Missing encrypted_name or status"}), 400

    try:
        result = update_offenders(file_path, encrypted_name, status)
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    return jsonify({
        "message": f"{result} offender {encrypted_name} with status {status}",
        "timestamp": get_current_timestamp()
    })

def passive_check_loop():
    while True:
        time.sleep(120)  # 2 minutes
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            continue

        updated_lines = []
        changed = False
        now = datetime.now()

        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = [part.strip() for part in line.split("!")]
            if len(parts) != 3:
                updated_lines.append(line + "\n")
                continue

            name, status, seen = parts
            try:
                seen_time = parse_timestamp(seen)
            except ValueError:
                updated_lines.append(line + "\n")
                continue

            if status == "active" and now - seen_time >= timedelta(minutes=2):
                updated_lines.append(f"{name} ! passive ! {seen}\n")
                changed = True
            else:
                updated_lines.append(line + "\n")

        if changed:
            with open(file_path, 'w') as f:
                f.writelines(updated_lines)

# Start the background thread when the app launches
threading.Thread(target=passive_check_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(port=6969, debug=True)
