/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ExecutiveDashboard extends Component {

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            period: "month",
            data: {
                global: {},
                conseillers: [],
                campagnes: [],
                is_admin: false,
            }
        });

        onWillStart(async () => {
            await this.fetchData();
        });
    }

    async fetchData() {
        const result = await this.orm.call(
            "oui.campaign",
            "get_executive_dashboard_data",
            [this.state.period]
        );

        this.state.data.global = result.global || {};
        this.state.data.conseillers = result.conseillers || [];
        this.state.data.campagnes = result.campagnes || [];
        this.state.data.is_admin = result.is_admin || false;
    }

    async changePeriod(period) {
        this.state.period = period;
        await this.fetchData();
    }

    openConseiller(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.users",
            res_id: id,
            views: [[false, "form"]],
        });
    }

    openCampaign(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "oui.campaign",
            res_id: id,
            views: [[false, "form"]],
        });
    }
}

ExecutiveDashboard.template = "ExecutiveDashboard";

/* 🔥 C'EST ÇA QUI MANQUAIT 🔥 */
registry.category("actions").add("executive_dashboard", ExecutiveDashboard);