import { AND, fields, Record } from "@mail/core/common/record";
import { rpc } from "@web/core/network/rpc";

export class MessageReactions extends Record {
    static id = AND("message", "content");

    /** @type {string} */
    content;
    /** @type {number} */
    count;
    /** @type {number} */
    sequence;
    partner_ids = fields.Many("Persona");
    guest_ids = fields.Many("Persona");
    personas = fields.Many("Persona", {
        compute() {
            return [...this.partner_ids, ...this.guest_ids];
        },
    });
    message = fields.One("mail.message");

    async remove() {
        this.store.insert(
            await rpc(
                "/mail/message/reaction",
                {
                    action: "remove",
                    content: this.content,
                    message_id: this.message.id,
                    ...this.message.thread.rpcParams,
                },
                { silent: true }
            )
        );
    }
}

MessageReactions.register();
