import { AND, Record } from "@mail/core/common/record";
import { rpc } from "@web/core/network/rpc";

export class MessageReactions extends Record {
    static id = AND("message", "content");
    /** @returns {import("models").MessageReactions} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").MessageReactions|import("models").MessageReactions[]} */
    static insert(data) {
        return super.insert(...arguments);
    }

    /** @type {string} */
    content;
    /** @type {number} */
    count;
    personas = Record.many("Persona");
    message = Record.one("Message");

    async remove() {
        await rpc(
            "/mail/message/reaction",
            {
                action: "remove",
                content: this.content,
                message_id: this.message.id,
            },
            { silent: true }
        );
    }
}

MessageReactions.register();
