from flask import Flask, render_template, request
import re

app = Flask(__name__)


@app.template_filter('format_currency')
def format_currency(value):
    return "₦{:,.0f}".format(value)


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
        "monthly": [("1.8GB", 1500), ("1.5GB", 2000), ("4.25GB", 3000), ("5.5GB", 3500), ("8GB", 3000), ("11GB", 5000),
                    ("15GB", 6500), ("20GB", 7500), ("25GB", 9000), ("32GB", 11000), ("75GB", 20000),
                    ("120GB", 22000), ("200GB", 30000)],
        "extended": [("30GB", 8000, "2 months"), ("100GB", 20000, "2 months"), ("160GB", 30000, "2 months"),
                     ("400GB", 50000, "3 months"), ("600GB", 75000, "3 months"), ("800GB", 90000, "6 months"),
                     ("1TB", 100000, "1 year"), ("2.5TB", 250000, "1 year"), ("4.5TB", 450000, "1 year")]
    },
    "Airtel": {
        "hourly": [("2GB", 200), ("5GB", 500)],
        "daily": [("40MB", 50), ("100MB", 100), ("200MB", 200), ("1GB", 500)],
        "weekly": [("750MB", 500), ("1GB", 500), ("6GB", 1500)],
        "monthly": [("1.5GB", 1000), ("4.5GB", 2000), ("4GB", 2500), ("8GB", 3000), ("10GB", 4000),
                    ("13GB", 5000), ("18GB", 6000), ("25GB", 8000)],
        "binge": [("1GB", 500), ("1.5GB + 2GB YouTube Night + 200MB (YouTube, Instagram & TikTok)", 600),
                  ("2GB + 2GB YouTube Night + 200MB (YouTube, Instagram & TikTok)", 750),
                  ("3GB + 2GB YouTube Night + 200MB (YouTube, Instagram & TikTok)", 1000)],
        "data_plus": [("4.5GB", 2000), ("15GB", 5000), ("30GB", 10000), ("60GB", 15000)]
    },
    "Glo": {
        "hourly": [("400MB", 100)],
        "daily": [("50MB", 50), ("150MB", 100), ("500MB", 200), ("1GB", 300), ("1.25GB", 500)],
        "weekly": [("1.8GB", 1000), ("2.5GB", 1500), ("4.1GB", 2000), ("5.8GB", 2500)],
        "monthly": [("10GB", 3000), ("22GB", 5000), ("50GB", 10000), ("93GB", 15000), ("119GB", 20000), ("138GB", 25000)],
        "mega": [("225GB", 30000, "30 days"), ("300GB", 36000, "30 days"),
                 ("425GB", 50000, "90 days"), ("525GB", 60000, "120 days"),
                 ("675GB", 75000, "120 days"), ("1TB", 100000, "1 year")],
        "youtube": [("500MB", 50, "1-hour streaming"), ("1.5GB", 130, "3-hour streaming"),
                    ("500MB", 50, "5-hour night streaming"), ("2GB", 200, "7-hour night streaming"),
                    ("5GB", 500, "10-hour streaming"), ("10GB", 1000, "30-hour streaming")],
        "my_g": [("400MB + 1-hour streaming", 100), ("1GB + 1-hour streaming", 300),
                 ("1.5GB + 1-hour streaming", 500), ("3.5GB + 1-hour streaming", 1000)]
    },
    "9mobile": {
        "daily": [("1GB", 525)],
        "weekly": [("7GB", 2250)],
        "monthly": [("9.5GB", 3750), ("22GB", 7500)]
    }
}

provider_ussd = {
    "MTN": "*312*88# for 1.5gb@200 and *121# for 13gb@2K",
    "Airtel": "*312#",
    "Glo": "*312#",
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