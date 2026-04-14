"""
SME Rule Reviewer Agent - CLI Version
Interactive CLI agent for risk SMEs to review and amend rules being applied when users create risks.
Runs in VS Code terminal - no Telegram required.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
import anthropic
from datetime import datetime
import re

# Load environment variables
load_dotenv()

class SMERuleReviewer:
    def __init__(self, rules_file='llm_merged_rules_keywords.json'):
        self.rules_file = rules_file
        self.rules = self.load_rules()
        self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.changes_made = []
        
    def load_rules(self):
        """Load rules from JSON file"""
        try:
            with open(self.rules_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Rules file '{self.rules_file}' not found.")
            return []
    
    def save_rules(self, backup=True):
        """Save rules back to JSON file"""
        if backup:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"{self.rules_file}.backup_{timestamp}"
            with open(backup_file, 'w') as f:
                json.dump(self.rules, f, indent=2)
            print(f"✅ Backup saved to: {backup_file}")
        
        with open(self.rules_file, 'w') as f:
            json.dump(self.rules, f, indent=2)
        print(f"✅ Rules saved to: {self.rules_file}")
    
    def display_rules(self, filter_keyword=None, start_index=0, max_display=10):
        """Display all rules or filtered rules"""
        if not self.rules:
            print("No rules available.")
            return
        
        rules_to_display = self.rules
        if filter_keyword:
            rules_to_display = [
                (i, r) for i, r in enumerate(self.rules, 1)
                if filter_keyword.lower() in str(r.get('description', '')).lower() 
                or filter_keyword.lower() in str(r.get('validation_criteria', '')).lower()
            ]
        else:
            rules_to_display = [(i, r) for i, r in enumerate(self.rules, 1)]
        
        if not rules_to_display:
            print(f"No rules found matching '{filter_keyword}'")
            return
        
        # Paginate
        end_index = min(start_index + max_display, len(rules_to_display))
        display_rules = rules_to_display[start_index:end_index]
        
        print(f"\n{'='*80}")
        print(f"Displaying rules {start_index + 1}-{end_index} of {len(rules_to_display)} total")
        print(f"{'='*80}\n")
        
        for idx, rule in display_rules:
            print(f"📋 Rule #{idx}")
            print(f"Description: {rule.get('description', 'N/A')}")
            print(f"Validation Criteria: {rule.get('validation_criteria', 'N/A')}")
            if 'rule_id' in rule:
                print(f"Rule ID: {rule['rule_id']}")
            print(f"{'-'*80}\n")
        
        if end_index < len(rules_to_display):
            print(f"💡 Tip: Type 'list {start_index + max_display}' to see more rules")
    
    def edit_rule(self, rule_index):
        """Edit a specific rule"""
        if rule_index < 1 or rule_index > len(self.rules):
            print(f"❌ Invalid rule index. Must be between 1 and {len(self.rules)}")
            return
        
        rule = self.rules[rule_index - 1]
        print(f"\n{'='*80}")
        print(f"Editing Rule #{rule_index}")
        print(f"{'='*80}")
        print(f"Current Description: {rule.get('description', 'N/A')}")
        print(f"Current Validation Criteria: {rule.get('validation_criteria', 'N/A')}")
        
        print("\nWhat would you like to edit?")
        print("1. Description")
        print("2. Validation Criteria")
        print("3. Both")
        print("4. Delete this rule")
        print("5. Cancel")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == '1':
            new_desc = input("\nEnter new description: ").strip()
            if new_desc:
                old_desc = rule.get('description')
                rule['description'] = new_desc
                self.changes_made.append({
                    'rule_index': rule_index,
                    'field': 'description',
                    'old_value': old_desc,
                    'new_value': new_desc,
                    'timestamp': datetime.now().isoformat()
                })
                print("✅ Description updated!")
        
        elif choice == '2':
            new_criteria = input("\nEnter new validation criteria: ").strip()
            if new_criteria:
                old_criteria = rule.get('validation_criteria')
                rule['validation_criteria'] = new_criteria
                self.changes_made.append({
                    'rule_index': rule_index,
                    'field': 'validation_criteria',
                    'old_value': old_criteria,
                    'new_value': new_criteria,
                    'timestamp': datetime.now().isoformat()
                })
                print("✅ Validation criteria updated!")
        
        elif choice == '3':
            new_desc = input("\nEnter new description: ").strip()
            new_criteria = input("Enter new validation criteria: ").strip()
            if new_desc and new_criteria:
                old_desc = rule.get('description')
                old_criteria = rule.get('validation_criteria')
                rule['description'] = new_desc
                rule['validation_criteria'] = new_criteria
                self.changes_made.append({
                    'rule_index': rule_index,
                    'field': 'both',
                    'old_values': {'description': old_desc, 'validation_criteria': old_criteria},
                    'new_values': {'description': new_desc, 'validation_criteria': new_criteria},
                    'timestamp': datetime.now().isoformat()
                })
                print("✅ Both fields updated!")
        
        elif choice == '4':
            confirm = input("\n⚠️  Are you sure you want to delete this rule? (yes/no): ").strip().lower()
            if confirm == 'yes':
                deleted_rule = self.rules.pop(rule_index - 1)
                self.changes_made.append({
                    'rule_index': rule_index,
                    'action': 'deleted',
                    'rule': deleted_rule,
                    'timestamp': datetime.now().isoformat()
                })
                print("✅ Rule deleted!")
        
        elif choice == '5':
            print("❌ Edit cancelled.")
    
    def add_new_rule(self):
        """Add a new rule"""
        print("\n" + "="*80)
        print("➕ Adding a new rule")
        print("="*80)
        description = input("Enter rule description: ").strip()
        validation_criteria = input("Enter validation criteria: ").strip()
        
        if description and validation_criteria:
            new_rule = {
                'description': description,
                'validation_criteria': validation_criteria
            }
            self.rules.append(new_rule)
            self.changes_made.append({
                'action': 'added',
                'rule': new_rule,
                'timestamp': datetime.now().isoformat()
            })
            print("✅ New rule added!")
        else:
            print("❌ Both description and validation criteria are required.")
    
    def ai_suggest_improvements(self, rule_index):
        """Use AI to suggest improvements to a rule"""
        if rule_index < 1 or rule_index > len(self.rules):
            print(f"❌ Invalid rule index. Must be between 1 and {len(self.rules)}")
            return
        
        rule = self.rules[rule_index - 1]
        
        prompt = f"""
You are a risk management expert. Review the following rule and suggest improvements to make it more clear, actionable, and effective.

Current Rule:
Description: {rule.get('description', 'N/A')}
Validation Criteria: {rule.get('validation_criteria', 'N/A')}

Provide suggestions for:
1. Improving clarity
2. Making criteria more specific and measurable
3. Any potential gaps or issues

Format your response as:
SUGGESTED DESCRIPTION: [improved description]
SUGGESTED CRITERIA: [improved criteria]
RATIONALE: [explanation of changes]
"""
        
        try:
            print("\n🤖 Analyzing rule with AI...")
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )
            
            suggestion = response.content[0].text
            print(f"\n{'='*80}")
            print("AI Suggestions:")
            print(f"{'='*80}")
            print(suggestion)
            print(f"{'='*80}\n")
            
            apply = input("Would you like to apply these suggestions? (yes/no): ").strip().lower()
            if apply == 'yes':
                # Extract suggested values (simple parsing)
                desc_match = re.search(r'SUGGESTED DESCRIPTION:\s*(.+?)(?:\n\n|SUGGESTED)', suggestion, re.IGNORECASE | re.DOTALL)
                crit_match = re.search(r'SUGGESTED CRITERIA:\s*(.+?)(?:\n\n|RATIONALE)', suggestion, re.IGNORECASE | re.DOTALL)
                
                if desc_match:
                    old_desc = rule.get('description')
                    new_desc = desc_match.group(1).strip()
                    rule['description'] = new_desc
                    print("✅ Description updated with AI suggestion!")
                
                if crit_match:
                    old_criteria = rule.get('validation_criteria')
                    new_crit = crit_match.group(1).strip()
                    rule['validation_criteria'] = new_crit
                    print("✅ Validation criteria updated with AI suggestion!")
                
                self.changes_made.append({
                    'rule_index': rule_index,
                    'action': 'ai_improved',
                    'ai_suggestion': suggestion,
                    'timestamp': datetime.now().isoformat()
                })
        
        except Exception as e:
            print(f"❌ Error getting AI suggestions: {e}")
    
    def view_changes(self):
        """Display all changes made in this session"""
        if not self.changes_made:
            print("\nNo changes made in this session.")
            return
        
        print(f"\n{'='*80}")
        print(f"📝 Changes Made This Session ({len(self.changes_made)} change(s)):")
        print(f"{'='*80}\n")
        
        for idx, change in enumerate(self.changes_made, 1):
            print(f"Change #{idx}:")
            if 'action' in change:
                if change['action'] == 'added':
                    print(f"  ➕ Added new rule: {change['rule'].get('description', '')[:60]}...")
                elif change['action'] == 'deleted':
                    print(f"  🗑️  Deleted Rule #{change['rule_index']}")
                elif change['action'] == 'ai_improved':
                    print(f"  🤖 AI-improved Rule #{change['rule_index']}")
            else:
                print(f"  ✏️  Modified Rule #{change['rule_index']} - {change['field']}")
            print(f"  Time: {change.get('timestamp', 'N/A')}")
            print(f"{'-'*80}\n")
    
    def search_rules(self, query):
        """Search rules using natural language with AI"""
        prompt = f"""
Given this search query from a risk SME: "{query}"

And these rules (showing first 20):
{json.dumps(self.rules[:20], indent=2)}

Identify which rules are most relevant to the query. Return the rule numbers (1-based) and explain briefly why they match.
Keep your response concise.
"""
        
        try:
            print("\n🔍 Searching rules with AI...")
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )
            
            print(f"\n{'='*80}")
            print("Search Results:")
            print(f"{'='*80}")
            print(response.content[0].text)
            print(f"{'='*80}\n")
        
        except Exception as e:
            print(f"❌ Error searching rules: {e}")
    
    def run(self):
        """Main interactive loop"""
        print("\n" + "="*80)
        print("🔧 SME Rule Reviewer Agent - CLI Version")
        print("Interactive tool for reviewing and amending risk assessment rules")
        print("="*80)
        print(f"\n📊 Loaded {len(self.rules)} rules from '{self.rules_file}'")
        
        while True:
            print("\n" + "-"*80)
            print("📌 Commands:")
            print("  list [start_index]  - List rules (optionally from a starting position)")
            print("  filter <keyword>    - Filter and display rules by keyword")
            print("  edit <number>       - Edit a specific rule by number")
            print("  add                 - Add a new rule")
            print("  delete <number>     - Delete a rule by number")
            print("  suggest <number>    - Get AI suggestions for improving a rule")
            print("  search <query>      - Search rules using natural language")
            print("  changes             - View all changes made this session")
            print("  save                - Save changes to file")
            print("  quit                - Exit without saving")
            print("  save-quit           - Save changes and exit")
            print("-"*80)
            
            command = input("\n💬 Enter command: ").strip()
            
            if not command:
                continue
            
            parts = command.split(maxsplit=1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            if cmd == 'list':
                start = int(args) if args.isdigit() else 0
                self.display_rules(start_index=start)
            
            elif cmd == 'filter':
                if args:
                    self.display_rules(filter_keyword=args)
                else:
                    print("❌ Usage: filter <keyword>")
            
            elif cmd == 'edit':
                if args.isdigit():
                    self.edit_rule(int(args))
                else:
                    print("❌ Usage: edit <number>")
            
            elif cmd == 'add':
                self.add_new_rule()
            
            elif cmd == 'delete':
                if args.isdigit():
                    self.edit_rule(int(args))  # Uses same method with delete option
                else:
                    print("❌ Usage: delete <number>")
            
            elif cmd == 'suggest':
                if args.isdigit():
                    self.ai_suggest_improvements(int(args))
                else:
                    print("❌ Usage: suggest <number>")
            
            elif cmd == 'search':
                if args:
                    self.search_rules(args)
                else:
                    print("❌ Usage: search <query>")
            
            elif cmd == 'changes':
                self.view_changes()
            
            elif cmd == 'save':
                if self.changes_made:
                    self.save_rules(backup=True)
                    print(f"✅ Saved {len(self.changes_made)} change(s).")
                else:
                    print("ℹ️  No changes to save.")
            
            elif cmd == 'quit':
                if self.changes_made:
                    confirm = input(f"\n⚠️  You have {len(self.changes_made)} unsaved change(s). Quit without saving? (yes/no): ").strip().lower()
                    if confirm != 'yes':
                        continue
                print("\n👋 Exiting without saving. Goodbye!")
                break
            
            elif cmd == 'save-quit':
                if self.changes_made:
                    self.save_rules(backup=True)
                    print(f"✅ Saved {len(self.changes_made)} change(s).")
                print("\n👋 Goodbye!")
                break
            
            else:
                print("❌ Unknown command. Type a command from the list above.")


if __name__ == "__main__":
    # You can specify a different rules file here if needed
    agent = SMERuleReviewer('llm_merged_rules_keywords.json')
    agent.run()
