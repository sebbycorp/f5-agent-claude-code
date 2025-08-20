#!/usr/bin/env python3

import requests
import time
import json
import urllib3
import threading
from datetime import datetime
from typing import Dict, List, Optional

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class F5Agent:
    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.username = username  
        self.password = password
        self.base_url = f"https://{host}/mgmt/tm"
        self.token = None
        self.session = requests.Session()
        self.session.verify = False
        self.monitoring = False
        self.last_pool_states = {}
        self.current_pool_members = []
        self.current_logs = []
        
    def authenticate(self) -> bool:
        """Authenticate with F5 and get auth token"""
        auth_url = f"https://{self.host}/mgmt/shared/authn/login"
        
        payload = {
            "username": self.username,
            "password": self.password,
            "loginProviderName": "tmos"
        }
        
        try:
            response = self.session.post(auth_url, json=payload, timeout=10)
            response.raise_for_status()
            
            auth_data = response.json()
            self.token = auth_data.get("token", {}).get("token")
            
            if self.token:
                self.session.headers.update({
                    "X-F5-Auth-Token": self.token,
                    "Content-Type": "application/json"
                })
                print(f"[{datetime.now()}] Authentication successful")
                return True
            else:
                print(f"[{datetime.now()}] Authentication failed - no token received")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"[{datetime.now()}] Authentication error: {e}")
            return False
    
    def get_system_logs(self) -> Optional[List[Dict]]:
        """Get system logs from F5"""
        try:
            url = f"{self.base_url}/sys/log"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get("entries", {})
            
        except requests.exceptions.RequestException as e:
            print(f"[{datetime.now()}] Error getting system logs: {e}")
            return None
    
    def get_pool_members(self) -> Optional[List[Dict]]:
        """Get all pool members and their states"""
        try:
            url = f"{self.base_url}/ltm/pool"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            pools = data.get("items", [])
            
            pool_info = []
            for pool in pools:
                pool_name = pool.get("name", "unknown")
                members_url = f"{self.base_url}/ltm/pool/{pool_name}/members"
                
                try:
                    members_response = self.session.get(members_url, timeout=10)
                    members_response.raise_for_status()
                    
                    members_data = members_response.json()
                    members = members_data.get("items", [])
                    
                    for member in members:
                        pool_info.append({
                            "pool": pool_name,
                            "member": member.get("name", "unknown"),
                            "state": member.get("state", "unknown"),
                            "session": member.get("session", "unknown"),
                            "address": member.get("address", "unknown"),
                            "connectionLimit": member.get("connectionLimit", 0)
                        })
                        
                except requests.exceptions.RequestException as e:
                    print(f"[{datetime.now()}] Error getting members for pool {pool_name}: {e}")
                    
            return pool_info
            
        except requests.exceptions.RequestException as e:
            print(f"[{datetime.now()}] Error getting pools: {e}")
            return None
    
    def get_virtual_servers(self) -> Optional[List[Dict]]:
        """Get virtual servers and their states"""
        try:
            url = f"{self.base_url}/ltm/virtual"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            virtuals = data.get("items", [])
            
            virtual_info = []
            for virtual in virtuals:
                virtual_info.append({
                    "name": virtual.get("name", "unknown"),
                    "destination": virtual.get("destination", "unknown"),
                    "enabled": virtual.get("enabled", False),
                    "pool": virtual.get("pool", "none")
                })
                
            return virtual_info
            
        except requests.exceptions.RequestException as e:
            print(f"[{datetime.now()}] Error getting virtual servers: {e}")
            return None
    
    def monitor_f5_background(self, interval: int = 30):
        """Background monitoring loop"""
        while self.monitoring:
            try:
                # Get system logs
                logs = self.get_system_logs()
                if logs:
                    self.current_logs = logs
                
                # Get pool member states
                pool_members = self.get_pool_members()
                if pool_members:
                    self.current_pool_members = pool_members
                    
                    # Check for state changes
                    for member in pool_members:
                        key = f"{member['pool']}/{member['member']}"
                        current_state = member['state']
                        
                        if key in self.last_pool_states:
                            if self.last_pool_states[key] != current_state:
                                print(f"\n[{datetime.now()}] STATE CHANGE: {key} {self.last_pool_states[key]} -> {current_state}")
                                print("> ", end="", flush=True)
                        
                        self.last_pool_states[key] = current_state
                
                time.sleep(interval)
                
            except Exception as e:
                print(f"\n[{datetime.now()}] Monitor error: {e}")
                print("> ", end="", flush=True)
                time.sleep(interval)
    
    def interactive_mode(self):
        """Interactive command interface"""
        print(f"[{datetime.now()}] Starting F5 Interactive Agent")
        print(f"[{datetime.now()}] Target: {self.host}")
        print("Type 'help' for commands or 'quit' to exit")
        print("-" * 60)
        
        if not self.authenticate():
            print("Failed to authenticate. Exiting.")
            return
        
        # Start background monitoring
        self.monitoring = True
        monitor_thread = threading.Thread(target=self.monitor_f5_background, daemon=True)
        monitor_thread.start()
        
        while True:
            try:
                command = input("> ").strip().lower()
                
                if command == "quit" or command == "exit":
                    self.monitoring = False
                    print("Goodbye!")
                    break
                elif command == "help":
                    self.show_help()
                elif command == "status":
                    self.show_status()
                elif command == "pools":
                    self.show_pools()
                elif command == "virtual" or command == "virtuals":
                    self.show_virtual_servers()
                elif command.startswith("pool "):
                    pool_name = command[5:]
                    self.show_pool_details(pool_name)
                elif command == "logs":
                    self.show_recent_logs()
                elif command == "summary":
                    self.show_summary()
                else:
                    print("Unknown command. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                self.monitoring = False
                print("\nGoodbye!")
                break
            except EOFError:
                self.monitoring = False
                print("\nGoodbye!")
                break
    
    def show_help(self):
        """Show available commands"""
        print("\nAvailable commands:")
        print("  help       - Show this help")
        print("  status     - Show overall F5 status")
        print("  pools      - List all pools and member states")
        print("  pool <name> - Show detailed info for specific pool")
        print("  virtual    - Show virtual servers")
        print("  logs       - Show recent system logs")
        print("  summary    - Show health summary")
        print("  quit       - Exit the agent")
        print()
    
    def show_status(self):
        """Show current F5 status"""
        print(f"\nF5 Status for {self.host}:")
        print(f"Connected: Yes")
        print(f"Last updated: {datetime.now()}")
        
        if self.current_pool_members:
            total_members = len(self.current_pool_members)
            up_members = len([m for m in self.current_pool_members if m['state'] == 'up'])
            down_members = len([m for m in self.current_pool_members if m['state'] == 'down'])
            
            print(f"Pool members: {total_members} total, {up_members} up, {down_members} down")
        print()
    
    def show_pools(self):
        """Show all pools and their member states"""
        if not self.current_pool_members:
            print("No pool data available.\n")
            return
        
        pools = {}
        for member in self.current_pool_members:
            pool_name = member['pool']
            if pool_name not in pools:
                pools[pool_name] = []
            pools[pool_name].append(member)
        
        print("\nPool Status:")
        for pool_name, members in pools.items():
            up_count = len([m for m in members if m['state'] == 'up'])
            total_count = len(members)
            print(f"  {pool_name}: {up_count}/{total_count} members up")
            
            for member in members:
                status_icon = "✓" if member['state'] == 'up' else "✗"
                print(f"    {status_icon} {member['member']} ({member['address']}) - {member['state']}")
        print()
    
    def show_pool_details(self, pool_name: str):
        """Show detailed info for a specific pool"""
        pool_members = [m for m in self.current_pool_members if m['pool'] == pool_name]
        
        if not pool_members:
            print(f"Pool '{pool_name}' not found.\n")
            return
        
        print(f"\nPool '{pool_name}' Details:")
        for member in pool_members:
            print(f"  Member: {member['member']}")
            print(f"    Address: {member['address']}")
            print(f"    State: {member['state']}")
            print(f"    Session: {member['session']}")
            print(f"    Connection Limit: {member['connectionLimit']}")
            print()
    
    def show_virtual_servers(self):
        """Show virtual servers"""
        virtuals = self.get_virtual_servers()
        if not virtuals:
            print("No virtual servers found.\n")
            return
        
        print("\nVirtual Servers:")
        for virtual in virtuals:
            status_icon = "✓" if virtual['enabled'] else "✗"
            print(f"  {status_icon} {virtual['name']}")
            print(f"    Destination: {virtual['destination']}")
            print(f"    Pool: {virtual['pool']}")
            print(f"    Enabled: {virtual['enabled']}")
            print()
    
    def show_recent_logs(self):
        """Show recent system logs"""
        if not self.current_logs:
            print("No log data available.\n")
            return
        
        print("\nRecent System Logs:")
        print(f"Found {len(self.current_logs)} log entries")
        print()
    
    def show_summary(self):
        """Show health summary"""
        print(f"\nF5 Health Summary for {self.host}:")
        
        if self.current_pool_members:
            total_members = len(self.current_pool_members)
            up_members = len([m for m in self.current_pool_members if m['state'] == 'up'])
            down_members = len([m for m in self.current_pool_members if m['state'] == 'down'])
            
            health_percentage = (up_members / total_members * 100) if total_members > 0 else 0
            
            print(f"Overall Health: {health_percentage:.1f}%")
            print(f"Pool Members: {up_members}/{total_members} operational")
            
            if down_members > 0:
                print("\nMembers DOWN:")
                for member in self.current_pool_members:
                    if member['state'] == 'down':
                        print(f"  ✗ {member['pool']}/{member['member']} ({member['address']})")
        
        virtuals = self.get_virtual_servers()
        if virtuals:
            enabled_vs = len([v for v in virtuals if v['enabled']])
            total_vs = len(virtuals)
            print(f"Virtual Servers: {enabled_vs}/{total_vs} enabled")
        
        print(f"Last Check: {datetime.now()}")
        print()

def main():
    # F5 connection details
    F5_HOST = "172.16.10.10"
    F5_USERNAME = "admin"
    F5_PASSWORD = "W3lcome098!"
    
    # Create and start the agent in interactive mode
    agent = F5Agent(F5_HOST, F5_USERNAME, F5_PASSWORD)
    agent.interactive_mode()

if __name__ == "__main__":
    main()