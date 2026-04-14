
import json

class RiskAgent:
    def __init__(self, rules):
        self.rules = rules

    def meets_rule(self, entry, rule):
        criteria = rule.get('validation_criteria', '').lower()
        description = str(entry).lower()
        keywords = [kw.strip() for kw in criteria.replace(',', ' ').split() if len(kw) > 2]
        return any(kw in description for kw in keywords)

    def classify(self, entry_text):
        matches = sum(self.meets_rule(entry_text, rule) for rule in self.rules)
        if matches >= max(2, int(0.5 * len(self.rules))):
            return 'good', matches
        elif matches > 0:
            return 'ok', matches
        else:
            return 'poor', matches

    def feedback(self, entry_text):
        matched_rules = [rule for rule in self.rules if self.meets_rule(entry_text, rule)]
        if matched_rules:
            return '\n'.join([f"- {rule['description']} (criteria: {rule['validation_criteria']})" for rule in matched_rules])
        else:
            return "No rules matched. Please review your entry for clarity and completeness."

def main():
    import tkinter as tk
    from tkinter import filedialog
    import os

    print("Please select your rules file (e.g., generated_rules.json)")
    root = tk.Tk()
    root.withdraw()
    rules_path = filedialog.askopenfilename(title="Select rules file", filetypes=[("JSON files", "*.json")])
    if not rules_path:
        print("No rules file selected. Exiting.")
        return
    print(f"Selected rules file: {rules_path}")
    try:
        with open(rules_path, 'r') as f:
            rules = json.load(f)
    except Exception as e:
        print(f"Error loading rules: {e}")
        return

    agent = RiskAgent(rules)
    print("Welcome to the Risk & Mitigation Chatbot! Type 'exit' at any prompt to quit.")
    import pandas as pd
    from datetime import datetime
    entries = []
    shortdate_str = datetime.now().strftime('%d%m%y')
    rules_dir = os.path.dirname(rules_path)
    xlsx_filename = os.path.join(rules_dir, f"{shortdate_str}_new_risks.xlsx")

    while True:
        risk = input("\nEnter your risk description: ").strip()
        if risk.lower() == 'exit':
            print("Goodbye!")
            break
        risk_classification, risk_matches = agent.classify(risk)
        print(f"Risk Classification: {risk_classification} (matched {risk_matches} rules)")
        risk_feedback = agent.feedback(risk)
        print("Relevant rules:")
        print(risk_feedback)
        if risk_classification == 'poor' or risk_feedback.startswith("No rules matched"):
            print("\nHelp: Your risk entry did not match any rules or was classified as 'poor'.")
            print("Tips for improvement:")
            print("- Be specific and clear about the risk.")
            print("- Include relevant keywords or criteria mentioned in the rules.")
            print("- Avoid vague language; describe the context and impact.")
            print("- If possible, review the rules and try to align your entry with their criteria.")

            def rule_score(entry, rule):
                criteria = rule.get('validation_criteria', '').lower()
                entry_words = set(str(entry).lower().split())
                rule_words = set(criteria.split())
                return len(entry_words & rule_words)

            best_rule = max(agent.rules, key=lambda r: rule_score(risk, r), default=None)
            if best_rule:
                print("\nSuggested template to reframe your risk entry:")
                print(f"Description: {best_rule['description']}")
                print(f"Criteria: {best_rule['validation_criteria']}")
                print("Try to describe your risk in a way that matches the above criteria.")

        mitigation = input("\nEnter your mitigation for this risk: ").strip()
        if mitigation.lower() == 'exit':
            print("Goodbye!")
            break
        mitigation_classification, mitigation_matches = agent.classify(mitigation)
        print(f"Mitigation Classification: {mitigation_classification} (matched {mitigation_matches} rules)")
        mitigation_feedback = agent.feedback(mitigation)
        print("Relevant rules:")
        print(mitigation_feedback)
        if mitigation_classification == 'poor' or mitigation_feedback.startswith("No rules matched"):
            print("\nHelp: Your mitigation entry did not match any rules or was classified as 'poor'.")
            print("Tips for improvement:")
            print("- Be specific and clear about the mitigation.")
            print("- Include relevant keywords or criteria mentioned in the rules.")
            print("- Avoid vague language; describe the context and impact.")
            print("- If possible, review the rules and try to align your entry with their criteria.")

            best_rule = max(agent.rules, key=lambda r: rule_score(mitigation, r), default=None)
            if best_rule:
                print("\nSuggested template to reframe your mitigation entry:")
                print(f"Description: {best_rule['description']}")
                print(f"Criteria: {best_rule['validation_criteria']}")
                print("Try to describe your mitigation in a way that matches the above criteria.")

        # Save entry to list
        entries.append({
            'Date': shortdate_str,
            'Risk': risk,
            'Risk Classification': risk_classification,
            'Mitigation': mitigation,
            'Mitigation Classification': mitigation_classification
        })

    # Write to Excel after each entry
    df = pd.DataFrame(entries)
    df.to_excel(xlsx_filename, index=False)
    print(f"Entry saved to {xlsx_filename}")

if __name__ == "__main__":
    main()
