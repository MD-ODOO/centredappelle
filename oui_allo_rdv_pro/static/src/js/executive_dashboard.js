/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class ExecutiveDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            data: {
                global: {},
                conseillers: [],
                campagnes: [],
                is_admin: false,
            },
            period: "month",
        });

        onWillStart(async () => {
            await this.fetchData();
        });
    }

    async fetchData() {
        const data = await this.orm.call(
            "oui.campaign",
            "get_executive_dashboard_data",
            [this.state.period]
        );

        this.state.data.global = data.global || {};
        this.state.data.conseillers = data.conseillers || [];
        this.state.data.campagnes = data.campagnes || [];
        this.state.data.is_admin = data.is_admin || false;
    }

    async changePeriod(period) {
        this.state.period = period;
        await this.fetchData();
    }

    openConseiller(conseillerId) {
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.users",
            res_id: conseillerId,
            views: [[false, "form"]],
        });
    }

    openCampaign(campId) {
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "oui.campaign",
            res_id: campId,
            views: [[false, "form"]],
        });
    }
}

ExecutiveDashboard.template = "ExecutiveDashboard";

registry.category("actions").add("executive_dashboard", ExecutiveDashboard);
