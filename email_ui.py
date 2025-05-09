import tkinter as tk
from tkinter import ttk, messagebox
import csv
from send_emails import send_email
from email_composer import EmailComposer

class EmailSenderUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Email Sender")
        self.root.geometry("800x600")
        
        # Initialize email composer
        self.composer = EmailComposer()
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create lead details display
        self.create_lead_details()
        
        # Create navigation buttons
        self.create_navigation()
        
        # Load leads
        self.leads = self.load_leads()
        self.current_index = 0
        self.display_current_lead()
    
    def create_lead_details(self):
        # Create labels and entry fields
        fields = ['Name', 'Email', 'Company', 'Position']
        self.entries = {}
        
        for i, field in enumerate(fields):
            ttk.Label(self.main_frame, text=f"{field}:").grid(row=i, column=0, sticky=tk.W, pady=5)
            entry = ttk.Entry(self.main_frame, width=50)
            entry.grid(row=i, column=1, sticky=tk.W, pady=5)
            self.entries[field.lower()] = entry
        
        # Email preview
        ttk.Label(self.main_frame, text="Email Preview:").grid(row=len(fields), column=0, sticky=tk.W, pady=5)
        self.email_preview = tk.Text(self.main_frame, height=10, width=60)
        self.email_preview.grid(row=len(fields), column=1, sticky=tk.W, pady=5)
        
        # Send button
        self.send_button = ttk.Button(self.main_frame, text="Send Email", command=self.send_current_email)
        self.send_button.grid(row=len(fields)+1, column=1, sticky=tk.W, pady=10)
    
    def create_navigation(self):
        nav_frame = ttk.Frame(self.main_frame)
        nav_frame.grid(row=len(self.entries)+2, column=0, columnspan=2, pady=10)
        
        ttk.Button(nav_frame, text="Previous", command=self.previous_lead).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav_frame, text="Next", command=self.next_lead).pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = ttk.Label(nav_frame, text="")
        self.status_label.pack(side=tk.LEFT, padx=20)
    
    def load_leads(self):
        leads = []
        try:
            with open('leads_with_messages.csv', mode='r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    leads.append(row)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load leads: {str(e)}")
        return leads
    
    def display_current_lead(self):
        if not self.leads:
            return
            
        lead = self.leads[self.current_index]
        
        # Update entry fields
        self.entries['name'].delete(0, tk.END)
        self.entries['name'].insert(0, lead.get('First Name', ''))
        
        self.entries['email'].delete(0, tk.END)
        self.entries['email'].insert(0, lead.get('Work Email', ''))
        
        self.entries['company'].delete(0, tk.END)
        self.entries['company'].insert(0, lead.get('Company', ''))
        
        self.entries['position'].delete(0, tk.END)
        self.entries['position'].insert(0, lead.get('Position', ''))
        
        # Generate and display email preview
        lead_info = {
            'name': lead.get('First Name', ''),
            'email': lead.get('Work Email', ''),
            'company': lead.get('Company', ''),
            'position': lead.get('Position', '')
        }
        
        email_content = self.composer.compose_email(lead_info)
        if email_content:
            self.email_preview.delete(1.0, tk.END)
            self.email_preview.insert(tk.END, f"Subject: {email_content['subject']}\n\n{email_content['body']}")
        
        # Update status
        self.status_label.config(text=f"Lead {self.current_index + 1} of {len(self.leads)}")
    
    def next_lead(self):
        if self.current_index < len(self.leads) - 1:
            self.current_index += 1
            self.display_current_lead()
    
    def previous_lead(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.display_current_lead()
    
    def send_current_email(self):
        if not self.leads:
            return
            
        lead = self.leads[self.current_index]
        lead_info = {
            'name': lead.get('First Name', ''),
            'email': lead.get('Work Email', ''),
            'company': lead.get('Company', ''),
            'position': lead.get('Position', '')
        }
        
        email_content = self.composer.compose_email(lead_info)
        if email_content:
            if send_email(lead_info['email'], email_content['subject'], email_content['body']):
                messagebox.showinfo("Success", f"Email sent successfully to {lead_info['email']}")
            else:
                messagebox.showerror("Error", f"Failed to send email to {lead_info['email']}")
        else:
            messagebox.showerror("Error", "Failed to generate email content")

def main():
    root = tk.Tk()
    app = EmailSenderUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 