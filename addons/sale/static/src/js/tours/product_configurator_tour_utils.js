import { queryAttribute } from '@odoo/hoot-dom';

function productSelector(productName) {
    return `
        table.o_sale_product_configurator_table
        tr:has(td>div[name="o_sale_product_configurator_name"]
        span:contains("${productName}"))
    `;
}

function optionalProductSelector(productName) {
    return `
        table.o_sale_product_configurator_table_optional
        tr:has(td>div[name="o_sale_product_configurator_name"]
        span:contains("${productName}"))
    `;
}

function optionalProductImageSrc(productName) {
    return queryAttribute(
        `${optionalProductSelector(productName)} td.o_sale_product_configurator_img>img`, 'src'
    );
}

function addOptionalProduct(productName) {
    return {
        content: `Add ${productName}`,
        trigger: `
            ${optionalProductSelector(productName)}
            td.o_sale_product_configurator_price
            button:contains("Add")
        `,
        run: 'click',
    };
}

function removeOptionalProduct(productName) {
    return {
        content: `Remove ${productName}`,
        trigger: `
            ${productSelector(productName)}
            td.o_sale_product_configurator_qty
            a:contains("Remove")
        `,
        run: 'click',
    };
}

function decreaseProductQuantity(productName) {
    return {
        content: `Decrease the quantity of ${productName}`,
        trigger: `
            ${productSelector(productName)}
            td.o_sale_product_configurator_qty
            button:has(i.fa-minus)
        `,
        run: 'click',
    };
}

function increaseProductQuantity(productName) {
    return {
        content: `Increase the quantity of ${productName}`,
        trigger: `
            ${productSelector(productName)}
            td.o_sale_product_configurator_qty
            button:has(i.fa-plus)
        `,
        run: 'click',
    };
}

function setProductQuantity(productName, quantity) {
    return {
        content: `Set the quantity of ${productName} to ${quantity}`,
        trigger: `
            ${productSelector(productName)}
            td.o_sale_product_configurator_qty
            input[name="sale_quantity"]
        `,
        run: `edit ${quantity} && click .modal-body`,
    };
}

function setProductUoM(productName, uomName) {
    // UoM must be enabled
    return {
        content: `Set the uom of ${productName} to ${uomName}`,
        trigger: `
            ${productSelector(productName)}
            label:contains("${uomName}")
        `,
        run: `click && click .modal-body`,
    };
}

function assertProductQuantity(productName, quantity) {
    return {
        content: `Assert that the quantity of ${productName} is ${quantity}`,
        trigger: `
            ${productSelector(productName)}
            td.o_sale_product_configurator_qty
            input[name="sale_quantity"]:value(${quantity})
        `,
    };
}

function selectAttribute(productName, attributeName, attributeValue, attributeType='radio') {
    const ptalSelector = `
        ${productSelector(productName)}
        td>div[name="ptal"]:has(label:contains("${attributeName}"))
    `;
    const content = `Select ${attributeValue} for ${productName} ${attributeName}`;
    switch (attributeType) {
        case 'color':
            return {
                content: content,
                trigger: `${ptalSelector} label[title="${attributeValue}"]`,
                run: 'click',
            };
        case 'multi':
        case 'pills':
        case 'radio':
            return {
                content: content,
                trigger: `${ptalSelector} span:contains("${attributeValue}")`,
                run: 'click',
            };
        case 'select':
            return {
                content: content,
                trigger: `${ptalSelector} select`,
                run: `selectByLabel ${attributeValue}`,
            };
        default:
            console.error("Unsupported attribute type");
    }
}

function setCustomAttribute(productName, attributeName, customValue) {
    return {
        content: `Set ${customValue} as a custom attribute for ${productName} ${attributeName}`,
        trigger: `
            ${productSelector(productName)}
            td>div[name="ptal"]:has(label:contains("${attributeName}"))
            input[type="text"]
        `,
        run: `edit ${customValue} && click .modal-body`,
    };
}

function selectAndSetCustomAttribute(
    productName, attributeName, attributeValue, customValue, attributeType='radio'
) {
    return [
        selectAttribute(productName, attributeName, attributeValue, attributeType),
        setCustomAttribute(productName, attributeName, customValue),
    ];
}

function assertPriceTotal(total) {
    return {
        content: `Assert that the total is ${total}`,
        trigger:
            `table.o_sale_product_configurator_table tr>td[colspan="4"] span:contains("${total}")`,
    };
}

function assertProductPrice(productName, price) {
    return {
        content: `Assert that ${productName} costs ${price}`,
        trigger: `
            ${productSelector(productName)}
            td.o_sale_product_configurator_price
            span:contains("${price}")
        `,
    };
}

function assertOptionalProductPrice(productName, price) {
    return {
        content: `Assert that ${productName} costs ${price}`,
        trigger: `
            ${optionalProductSelector(productName)}
            td.o_sale_product_configurator_qty
            span:contains("${price}")
        `,
    };
}

function assertProductPriceInfo(productName, priceInfo) {
    return {
        content: `Assert that the price info of ${productName} is ${priceInfo}`,
        trigger: `
            ${productSelector(productName)}
            td.o_sale_product_configurator_price
            div:contains("${priceInfo}")
        `,
    };
}

function assertOptionalProductPriceInfo(productName, priceInfo) {
    return {
        content: `Assert that the price info of ${productName} is ${priceInfo}`,
        trigger: `
            ${optionalProductSelector(productName)}
            td.o_sale_product_configurator_qty
            div:contains("${priceInfo}")
        `,
    };
}

function assertProductNameContains(productName) {
    return {
        content: `Assert that the product name contains ${productName}`,
        trigger: productSelector(productName),
    };
}

function assertFooterButtonsDisabled() {
    return {
        content: "Assert that the footer buttons are disabled",
        trigger: '.o_sale_product_configurator_dialog footer.modal-footer button:disabled',
    };
}

function saveConfigurator() {
    return [
        {
            trigger: '.o_sale_product_configurator_dialog button:contains(Confirm)',
            run: 'click',
        }, {
            content: "Wait until the modal is closed",
            trigger: 'body:not(:has(.o_sale_product_configurator_dialog))',
        }
    ];
}

export default {
    productSelector,
    optionalProductSelector,
    optionalProductImageSrc,
    addOptionalProduct,
    removeOptionalProduct,
    increaseProductQuantity,
    decreaseProductQuantity,
    setProductQuantity,
    setProductUoM,
    assertProductQuantity,
    selectAttribute,
    setCustomAttribute,
    selectAndSetCustomAttribute,
    assertPriceTotal,
    assertProductPrice,
    assertOptionalProductPrice,
    assertProductPriceInfo,
    assertOptionalProductPriceInfo,
    assertProductNameContains,
    assertFooterButtonsDisabled,
    saveConfigurator,
};
