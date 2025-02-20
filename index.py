from flask import Flask, render_template, request

app = Flask(__name__)

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

def find_best_plan(provider, budget):
    best_plan = None
    for duration, plans in network_providers[provider].items():
        for plan_info in plans:
           
            plan_name = plan_info[0]
            plan_price = plan_info[1]
            plan_duration = duration

            if plan_price <= budget and (best_plan is None or plan_price > best_plan[1]):
                best_plan = (plan_name, plan_price, plan_duration)
    
    return best_plan

@app.route('/', methods=['GET', 'POST'])
def index():
    best_plan = None
    if request.method == 'POST':
        budget = request.form.get('budget')
        provider = request.form.get('provider')

        if budget and provider in network_providers:
            try:
                budget = int(budget)
                best_plan = find_best_plan(provider, budget)
            except ValueError:
                best_plan = None  

    return render_template('index.html', best_plan=best_plan, providers=network_providers.keys())

if __name__ == '__main__':
   
    app.run(host="0.0.0.0", debug=False)

