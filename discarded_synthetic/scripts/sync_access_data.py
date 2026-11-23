import json

with open("data/full_100_verified.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Update the specific apps to remove contradictions
# WhatsApp Business (#28)
data["28"]["access_model"] = "Partner / Admin Approval"
data["28"]["buildable_today"] = "Partial"
data["28"]["main_blocker"] = "Partner / Admin Approval"

# Google Ads (#31)
data["31"]["access_model"] = "Partner / Admin Approval"
data["31"]["buildable_today"] = "Partial"
data["31"]["main_blocker"] = "Partner / Admin Approval"

# Meta Ads (#32)
data["32"]["access_model"] = "Partner / Admin Approval"
data["32"]["buildable_today"] = "Partial"
data["32"]["main_blocker"] = "Partner / Admin Approval"

# LinkedIn Ads (#33)
data["33"]["access_model"] = "Partner / Admin Approval"
data["33"]["buildable_today"] = "Partial"
data["33"]["main_blocker"] = "Partner / Admin Approval"

# Sherlock (#58)
data["58"]["access_model"] = "Open Source / Local CLI"
data["58"]["buildable_today"] = "Yes"
data["58"]["main_blocker"] = "No Hosted API (Local CLI)"

# Mermaid CLI (#98)
data["98"]["access_model"] = "Open Source / Local CLI"
data["98"]["buildable_today"] = "Yes"
data["98"]["main_blocker"] = "No Hosted API (Local CLI)"

# fanbasis (#50)
data["50"]["access_model"] = "Closed Platform"
data["50"]["buildable_today"] = "No"
data["50"]["main_blocker"] = "No Public API"

# Save updated dataset
with open("data/full_100_verified.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Synchronized all access models and blockers in full_100_verified.json.")
