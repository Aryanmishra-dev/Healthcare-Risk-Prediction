import re

with open("app/templates/index.html", "r") as f:
    html = f.read()

# Replace diabetes form
diab_pattern = re.compile(r'<!-- Left: Form -->\s*<div class="lg:col-span-7 flex flex-col gap-6">\s*<form hx-post="/predict/diabetes.*?</form>\s*</div>', re.DOTALL)
html = diab_pattern.sub('<!-- Left: Form -->\n                {% include "partials/diabetes_form.html" %}', html)

# Replace heart disease form
heart_pattern = re.compile(r'<!-- Left: Form -->\s*<div class="lg:col-span-7 flex flex-col gap-6">\s*<form hx-post="/predict/heart.*?</form>\s*</div>', re.DOTALL)
html = heart_pattern.sub('<!-- Left: Form -->\n                {% include "partials/heart_form.html" %}', html)

# Replace lung cancer form
lung_pattern = re.compile(r'<!-- Left: Form -->\s*<div class="lg:col-span-7 flex flex-col gap-6">\s*<form hx-post="/predict/lung.*?</form>\s*</div>', re.DOTALL)
html = lung_pattern.sub('<!-- Left: Form -->\n                {% include "partials/lung_form.html" %}', html)

with open("app/templates/index.html", "w") as f:
    f.write(html)
