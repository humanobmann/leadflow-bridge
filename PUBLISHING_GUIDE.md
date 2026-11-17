# Publication instructions / Veröffentlichungsanleitung

## 1. GitHub

The correct personal owner for this freelancer project is the GitHub user **humanobmann**, not a political group or the Menschlichkeit Österreich organization. No repository has been created or uploaded by this package.

1. Review repository contents and rights to all included assets.
2. Create a **public** personal repository named `leadflow-bridge` at https://github.com/new without initializing it with GitHub's README.
3. Unzip the archive; open a terminal inside the `leadflow-bridge` project directory.
4. Run:

```bash
git init
git branch -M main
git add .
git commit -m "Publish LeadFlow Bridge portfolio demo v2.0"
git remote add origin https://github.com/humanobmann/leadflow-bridge.git
git push -u origin main
```

These commands publish the project to your **own new** repository. Do not run them in another existing work repository. GitHub authentication and repository creation must be completed separately.

## 2. Upwork Portfolio

Open your Upwork freelancer profile and use the **Portfolio** section to add a new project. Paste the English title and text from [PORTFOLIO_UPWORK.md](PORTFOLIO_UPWORK.md). Mark the item as an **independent demonstration**, not a customer assignment.

Upload the three images **in this order**, from the `assets/upwork/` folder:

1. `01_portfolio_cover.png`
2. `02_demo_dashboard.png`
3. `03_architecture.png`

Each is **1000 × 750 pixels (4:3)**, in PNG format. Upwork's official recommendation is 1000 × 750 for portfolio images: https://support.upwork.com/hc/en-us/articles/360016144974-How-to-enhance-your-freelancer-profile

After the GitHub repository is published, include its verified URL as supporting evidence. The ChatGPT Upwork plugin available in this workflow cannot publish portfolio items directly, so this step must be completed through the website or a browser-enabled Work workflow with authorization.

## 3. Final public claims review

Allowed after re-running tests: "Independently built local Python integration demo; 21 automated tests, CSV validation, bounded retries, idempotent REST API, read-only dashboard, and end-to-end localhost smoke test."

Do **not** claim: a HubSpot/Salesforce integration, real customer project, client testimonials, commercial performance gains, production security certification or passing cloud CI runs that have not actually executed.

## Deutsch kurz

Im persönlichen GitHub-Konto `humanobmann` ein neues, leeres öffentliches Repository `leadflow-bridge` anlegen. Das bereinigte ZIP entpacken und nur dort hochladen. Anschließend bei Upwork unter Portfolio ein eigenes Demonstrationsprojekt erstellen. Die drei Bilder aus `assets/upwork/` verwenden und die englische Beschreibung aus `PORTFOLIO_UPWORK.md` einfügen. Das Projekt nicht als Kundenauftrag darstellen.
