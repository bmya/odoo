import { registry } from "@web/core/registry";
import { floatField, FloatField } from "@web/views/fields/float/float_field";

const fieldRegistry = registry.category("fields");

class FloatWithoutTrailingZeros extends FloatField {
    get formattedValue() {
        return super.formattedValue.replace(/^([\d,]+)$|^([\d,]+)\.0*$|^([\d,]+\.\d*?)0*$/, "$1$2$3");
    }
}

const floatWithoutTrailingZeros = { ...floatField, component: FloatWithoutTrailingZeros };

fieldRegistry.add("float_without_trailing_zeros", floatWithoutTrailingZeros);
