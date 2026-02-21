/** oui_allo_rdv_pro/static/src/js/executive_dashboard.js **/

odoo.define('oui_allo_rdv_pro.executive_dashboard', function(require) {
    "use strict";

    const { Component, useState, onMounted } = owl;
    const rpc = require('web.rpc');
    const { _t } = require('web.core');

    class ExecutiveDashboard extends Component {
        constructor() {
            super(...arguments);
            this.state = useState({
                data: {
                    global: {},
                    conseillers: [],
                    campagnes: [],
                    is_admin: false,
                },
                period: 'month',
            });
        }

        async fetchData() {
            try {
                const data = await rpc.query({
                    model: 'oui.campaign',
                    method: 'get_executive_dashboard_data',
                    args: [this.state.period],
                });

                this.state.data.global = data.global ?? {};
                this.state.data.conseillers = data.conseillers ?? [];
                this.state.data.campagnes = data.campagnes ?? [];
                this.state.data.is_admin = data.is_admin ?? false;

            } catch (err) {
                console.error("Erreur lors du chargement des données du dashboard :", err);
            }
        }

        changePeriod(period) {
            this.state.period = period;
            this.fetchData();
        }

        openConseiller(conseillerId) {
            return this.env.services.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'res.users',
                res_id: conseillerId,
                views: [[false, 'form']],
            });
        }

        openCampaign(campId) {
            return this.env.services.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'oui.campaign',
                res_id: campId,
                views: [[false, 'form']],
            });
        }

        onMounted() {
            this.fetchData();
        }
    }

    ExecutiveDashboard.template = 'ExecutiveDashboard';

    return ExecutiveDashboard;
});