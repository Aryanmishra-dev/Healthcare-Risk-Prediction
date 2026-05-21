import re

with open("frontend/src/pages/templates/index.html", "r") as f:
    content = f.read()

# Add to navigation
nav_item_dashboard = """
                <a id="nav-dashboard" href="/dashboard" onclick="switchTab('dashboard');return false"
                   class="nav-link flex items-center gap-2 px-3 py-2 rounded-lg {% if initial_tab == 'dashboard' %}bg-primary/10 text-primary shadow-sm{% else %}text-slate-600 hover:bg-slate-100 hover:text-slate-900{% endif %} transition-colors whitespace-nowrap">
                    <span class="material-symbols-outlined text-[20px]">dashboard</span>
                    <span class="text-sm {% if initial_tab == 'dashboard' %}font-bold{% else %}font-medium{% endif %}">Dashboard</span>
                </a>
"""
# Insert after the lung cancer nav link
content = content.replace("</a>\n                </nav>", "</a>" + nav_item_dashboard + "                </nav>")

# Add section panels
section_panels = """
        <!-- ══════════════ DASHBOARD SECTION ══════════════ -->
        <div class="section-panel {% if initial_tab == 'dashboard' %}active{% endif %}" id="section-dashboard">
            {% include "partials/dashboard.html" ignore missing %}
        </div>
        <div class="section-panel {% if initial_tab == 'dashboard_uploads' %}active{% endif %}" id="section-dashboard_uploads">
            {% include "partials/dashboard_uploads.html" ignore missing %}
        </div>
        <div class="section-panel {% if initial_tab == 'dashboard_history' %}active{% endif %}" id="section-dashboard_history">
            {% include "partials/dashboard_history.html" ignore missing %}
        </div>
        <div class="section-panel {% if initial_tab == 'dashboard_sessions' %}active{% endif %}" id="section-dashboard_sessions">
            {% include "partials/dashboard_sessions.html" ignore missing %}
        </div>
        <div class="section-panel {% if initial_tab == 'dashboard_profile' %}active{% endif %}" id="section-dashboard_profile">
            {% include "partials/dashboard_profile.html" ignore missing %}
        </div>
"""
content = content.replace("        </div>\n    </div>\n</main>", section_panels + "        </div>\n    </div>\n</main>")

# Update switchTab logic mappings
# Add dashboard paths to tabPaths and pathTabs
tabPaths_repl = """var tabPaths = {
    'home': '/',
    'about': '/about',
    'diabetes': '/diabetes',
    'heart': '/heart-disease',
    'lung': '/lung-cancer',
    'dashboard': '/dashboard',
    'dashboard_uploads': '/dashboard/uploads',
    'dashboard_history': '/dashboard/history',
    'dashboard_sessions': '/dashboard/sessions',
    'dashboard_profile': '/dashboard/profile'
};"""
content = re.sub(r"var tabPaths = \{[^}]+\};", tabPaths_repl, content)

pathTabs_repl = """var pathTabs = {
    '/': 'home',
    '/about': 'about',
    '/diabetes': 'diabetes',
    '/heart-disease': 'heart',
    '/lung-cancer': 'lung',
    '/dashboard': 'dashboard',
    '/dashboard/uploads': 'dashboard_uploads',
    '/dashboard/history': 'dashboard_history',
    '/dashboard/sessions': 'dashboard_sessions',
    '/dashboard/profile': 'dashboard_profile'
};"""
content = re.sub(r"var pathTabs = \{[^}]+\};", pathTabs_repl, content)

with open("frontend/src/pages/templates/index.html", "w") as f:
    f.write(content)
print("Index patched")
