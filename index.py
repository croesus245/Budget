from flask import Flask, render_template, request
import re

app = Flask(__name__)

# Custom filter for currency formatting
@app.template_filter('format_currency')
def format_currency(value):
    return "₦{:,.0f}".format(value)

# Custom filter for GB formatting
@app.template_filter('format_gb')
def format_gb(value):
    return "{:.1f}GB".format(value/1000) if value >= 1000 else "{:.0f}MB".format(value)

def parse_data_allowance(plan_name):
    """Convert data allowance string to MB as integer"""
    match = re.match(r"([\d.]+)\s*([GTM]B)", plan_name, re.IGNORECASE)
    if not match:
        return 0
    amount, unit = match.groups()
    amount = float(amount)
    unit = unit.upper()
    if unit == 'TB':
        return int(amount * 1e6)
    elif unit == 'GB':
        return int(amount * 1000)
    elif unit == 'MB':
        return int(amount)
    return 0

network_providers = {
    "MTN": {
        "hourly": [("400MB", 100)],
        "daily": [("75MB", 75), ("1GB", 350), ("2.5GB", 600)],
        "weekly": [("5GB", 1500)],
        "monthly": [("1.8GB", 1500), ("4.25GB", 3000), ("5.5GB", 3500), ("8GB", 3000), ("11GB", 5000),
                    ("15GB", 6500), ("20GB", 7500), ("25GB", 9000), ("32GB", 11000), ("75GB", 20000),
                    ("120GB", 22000), ("200GB", 30000)],
        "extended": [("30GB", 8000, "2 months"), ("100GB", 20000, "2 months"), ("160GB", 30000, "2 months"),
                     ("400GB", 50000, "3 months"), ("600GB", 75000, "3 months"), ("800GB", 90000, "6 months"),
                     ("1TB", 100000, "1 year"), ("2.5TB", 250000, "1 year"), ("4.5TB", 450000, "1 year")]
    },
    "Airtel": {
        "daily": [("1GB", 525)],
        "weekly": [("5GB", 2250)],
        "monthly": [("2GB", 1500), ("3GB", 2000), ("4GB", 2500), ("8GB", 3000), ("10GB", 4000),
                     ("13GB", 5000), ("18GB", 6000), ("25GB", 8000)]
    },
    "Glo": {
        "daily": [("1GB", 525)],
        "weekly": [("1.25GB", 525)],
        "monthly": [("10.8GB", 3000), ("24GB", 7500)]
    },
    "9mobile": {
        "daily": [("1GB", 525)],
        "weekly": [("7GB", 2250)],
        "monthly": [("9.5GB", 3750), ("22GB", 7500)]
    }
}

provider_ussd = {
    "MTN": "*131#",
    "Airtel": "*141#",
    "Glo": "*127*0#",
    "9mobile": "*200#"
}

def get_eligible_plans(provider, budget):
    eligible_plans = {
        'hourly': [],
        'daily': [],
        'weekly': [],
        'monthly': [],
        'extended': []
    }
    
    for duration_key, plans in network_providers[provider].items():
        for plan in plans:
            if duration_key == "extended":
                plan_name, price, duration = plan
            else:
                plan_name, price = plan[:2]
                duration = duration_key
            
            if price > budget:
                continue
            
            data_mb = parse_data_allowance(plan_name)
            if not data_mb:
                continue
            
            data_gb = data_mb / 1000
            cost_per_gb = price / data_gb if data_gb > 0 else 0
            value_score = data_mb / price if price > 0 else 0
            
            plan_details = {
                'name': plan_name,
                'price': price,
                'duration': duration,
                'data_mb': data_mb,
                'data_gb': data_gb,
                'cost_per_gb': cost_per_gb,
                'value_score': value_score
            }
            
            category = 'extended' if duration_key == 'extended' else duration_key
            eligible_plans[category].append(plan_details)
    
    # Sort plans in each category by value score (descending) and price (ascending)
    for category in eligible_plans:
        eligible_plans[category].sort(
            key=lambda x: (-x['value_score'], x['price']),
            reverse=False
        )
    
    return eligible_plans

@app.route('/', methods=['GET', 'POST'])
def index():
    eligible_plans = None
    selected_provider = None
    error = None
    searched = False
    ussd_code = None

    if request.method == 'POST':
        searched = True
        budget_str = request.form.get('budget', '').strip()
        provider = request.form.get('provider')
        
        if not provider or provider not in network_providers:
            error = "Please select a valid network provider."
        else:
            try:
                budget = int(budget_str)
                if budget <= 0:
                    error = "Budget must be a positive number."
                else:
                    eligible_plans = get_eligible_plans(provider, budget)
                    ussd_code = provider_ussd.get(provider)
            except ValueError:
                error = "Please enter a valid numeric budget."

        selected_provider = provider

    return render_template(
        'index.html',
        eligible_plans=eligible_plans,
        providers=network_providers.keys(),
        selected_provider=selected_provider,
        error=error,
        searched=searched,
        ussd_code=ussd_code,
        categories=['hourly', 'daily', 'weekly', 'monthly', 'extended']
    )

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)