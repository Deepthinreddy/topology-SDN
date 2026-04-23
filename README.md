# SDN Topology with Dynamic Link Failure Handling (Mininet + Ryu)

## 📌 Project Overview

This project demonstrates a Software Defined Networking (SDN) setup using:

* **Mininet** (network emulation)
* **Ryu Controller** (SDN controller using OpenFlow)

The network supports:

* Basic connectivity between hosts
* Dynamic topology monitoring
* Handling of link failures
* Reconfiguration of network paths

---

## 🏗️ Network Topology

Tree topology (depth = 2):

```
    s1
   /  \
 s2    s3
/ \    / \
```

h1  h2  h3  h4

---

## ⚙️ Technologies Used

* Python
* Mininet
* Ryu Controller
* OpenFlow 1.3

---

## 📁 Project Structure

```
topology-SDN/
│── controller.py        # Ryu controller logic
│── topo.py              # Custom topology (with alternate paths)
│── README.md
```

---

## 🚀 How to Run

### Step 1: Activate Environment

```bash
source ~/ryu-env/bin/activate
```

---

### Step 2: Start Ryu Controller

```bash
ryu-manager controller.py
```

---

### Step 3: Run Mininet

```bash
sudo mn --custom topo.py --topo mytopo --controller=remote
```

---

### Step 4: Test Connectivity

```bash
pingall
```

---

## 🔁 Link Failure Simulation

To simulate link failure:

```bash
link s1 s2 down
```

Check connectivity again:

```bash
pingall
```

---

## 🔄 Reconfiguration Logic

When a link goes down:

* Controller detects topology change
* Clears flow rules
* Re-learns MAC addresses
* Uses alternate path (if available)

---


## 📊 Observations

* Network works fully before failure (0% packet loss)
* Packet loss occurs after link failure
* Alternate path enables partial/complete recovery
* Controller dynamically adapts to topology changes

---

## ⚠️ Notes

* Ensure Ryu controller is running before Mininet
* Use OpenFlow 1.3 compatible controller
* Avoid committing virtual environments to GitHub

---

## 👩‍💻 Author

Deepthi Reddy

---

## 📌 Conclusion

This project demonstrates how SDN enables dynamic control of networks, allowing real-time adaptation to failures using a centralized controller.
