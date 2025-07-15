Here's a complete and professional `README.md` section for setting up and running your ASTM Analyzer Simulator application, including Python, virtual serial ports, and socket communication:

---

# 🧪 ASTM Analyzer Simulator – Setup Guide

This application is designed to simulate communication between laboratory analyzers and middleware systems using the ASTM protocol over both **serial** and **TCP/IP** sockets.

---

## ✅ Prerequisites

Before running the application, ensure the following requirements are fulfilled:

### 1. ✅ Python Installation

* Make sure **Python 3.10+** is installed on your system.
* To check, run:

```bash
python --version
```

* If not installed, download Python from: [https://www.python.org/downloads/](https://www.python.org/downloads/)

Make sure to check **"Add Python to PATH"** during installation.

---

### 2. ✅ Virtual Serial Ports Setup (For Testing Serial Communication)

If your system **does not have physical COM ports**, you need to simulate them using virtual ports.

#### ▶ Steps to Set Up Virtual COM Ports (Windows):

1. **Download Virtual Serial Port Control**:

   * Visit: [https://www.fabulatech.com/virtual-serial-port-control-download.html](https://www.fabulatech.com/virtual-serial-port-control-download.html)
   * Download the **64-bit `.msi` installer** for Windows.

2. **Install the Application**:

   * Run the downloaded installer.
   * Follow the on-screen setup instructions.

3. **Launch the Tool**:

   * Open the app via:

     * Start Menu → Search for **"Virtual Serial Port Tools"**, or
     * Launch it directly from the desktop if a shortcut is available.

4. **Activate Limited Mode (Free Usage)**:

   * When prompted, choose **“Limited Features”**.
   * This is sufficient for development and local testing.

5. **Create a Local Bridge**:

   * From the main interface, select **"Local Bridge"**.
   * This will create **two COM ports** (e.g., `COM2` and `COM3`) that are internally connected to each other.
   * These ports will act as a loopback testbed for your application.

---

## 🛠️ Installation Steps

1. **Clone or Download the Project**:

```bash
git clone https://github.com/your-username/astm-analyzer-simulator.git
cd astm-analyzer-simulator
```

2. **Install Dependencies** (if any):

If you use external packages (e.g., `pyserial`), install them:

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install pyserial
```

> *(Optional) Create a virtual environment with `python -m venv venv` for isolation.*

---

## 🚀 Running the Application

Run the main UI script:

```bash
python UI.py
```

* A GUI window will launch.
* Use **COM2** (or whatever virtual port you selected) as the device port.
* Configure baud rate (e.g., 9600).
* Connect to a **TCP server** at `127.0.0.1:15200` (you should run a test server first).
* Use the **Send** or **ENQ** buttons to simulate ASTM messaging.

---

## 📋 Notes

* ASTM messages should be sent in **raw bytes**, including control characters like `STX`, `ETX`, `ACK`, etc.
* All communication events will be logged in the GUI with timestamps.
* Serial messages can be tested using the virtual COM bridge (`COM2` → `COM3` loopback).
* TCP messages can be tested with a local test server listening on port `15200`.

---

## 📞 Troubleshooting

* **"Connection refused" error**:

  * Ensure the target TCP server is running and listening at the specified host\:port.

* **"Port not found"**:

  * Make sure your COM ports exist. Check in **Device Manager** under "Ports (COM & LPT)".

* **Permission denied / access issues**:

  * Run the script with administrator privileges.

---

Let me know if you'd like a sample server script or test messages to include in the README as well.