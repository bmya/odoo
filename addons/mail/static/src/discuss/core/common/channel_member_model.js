import { Store } from "@mail/core/common/store_service";
import { fields, Record } from "@mail/core/common/record";

import { browser } from "@web/core/browser/browser";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { user } from "@web/core/user";

const { DateTime } = luxon;

export class ChannelMember extends Record {
    static _name = "discuss.channel.member";
    static id = "id";

    /** @type {string} */
    create_date;
    /** @type {number} */
    id;
    last_interest_dt = fields.Datetime();
    last_seen_dt = fields.Datetime();
    persona = fields.One("Persona", { inverse: "channelMembers" });
    thread = fields.One("Thread", { inverse: "channel_member_ids" });
    threadAsSelf = fields.One("Thread", {
        compute() {
            if (this.store.self?.eq(this.persona)) {
                return this.thread;
            }
        },
    });
    fetched_message_id = fields.One("mail.message");
    seen_message_id = fields.One("mail.message");
    syncUnread = true;
    _syncUnread = fields.Attr(false, {
        compute() {
            if (!this.syncUnread || !this.eq(this.thread?.selfMember)) {
                return false;
            }
            return (
                this.localNewMessageSeparator !== this.new_message_separator ||
                this.localMessageUnreadCounter !== this.message_unread_counter
            );
        },
        onUpdate() {
            if (this._syncUnread) {
                this.localNewMessageSeparator = this.new_message_separator;
                this.localMessageUnreadCounter = this.message_unread_counter;
            }
        },
    });
    unreadSynced = fields.Attr(true, {
        compute() {
            return this.localNewMessageSeparator === this.new_message_separator;
        },
        onUpdate() {
            if (this.unreadSynced) {
                this.hideUnreadBanner = false;
            }
        },
    });
    hideUnreadBanner = false;
    localMessageUnreadCounter = 0;
    localNewMessageSeparator = null;
    message_unread_counter = 0;
    message_unread_counter_bus_id = 0;
    new_message_separator = null;
    threadAsTyping = fields.One("Thread", {
        compute() {
            return this.isTyping ? this.thread : undefined;
        },
        eager: true,
        onAdd() {
            browser.clearTimeout(this.typingTimeoutId);
            this.typingTimeoutId = browser.setTimeout(
                () => (this.isTyping = false),
                Store.OTHER_LONG_TYPING
            );
        },
        onDelete() {
            browser.clearTimeout(this.typingTimeoutId);
        },
    });
    /** @type {number} */
    typingTimeoutId;

    get name() {
        return this.persona.name;
    }

    /**
     * @returns {string}
     */
    getLangName() {
        return this.persona.lang_name;
    }

    get memberSince() {
        return this.create_date ? deserializeDateTime(this.create_date) : undefined;
    }

    /**
     * @param {import("models").Message} message
     */
    hasSeen(message) {
        return this.persona.eq(message.author) || this.seen_message_id?.id >= message.id;
    }
    get lastSeenDt() {
        return this.last_seen_dt
            ? this.last_seen_dt.toLocaleString(DateTime.TIME_24_SIMPLE, {
                  locale: user.lang,
              })
            : undefined;
    }

    get totalUnreadMessageCounter() {
        let counter = this.message_unread_counter;
        if (!this.unreadSynced) {
            counter += this.localMessageUnreadCounter;
        }
        return counter;
    }
}

ChannelMember.register();
