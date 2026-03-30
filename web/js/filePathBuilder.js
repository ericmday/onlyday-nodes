import { app } from "/scripts/app.js";

console.log("[FilePathBuilder] JS extension loaded");

const MAX_FOLDER_VARS = 5;
const MAX_FILENAME_VARS = 5;

function parseVariables(template) {
    const matches = template.match(/\{(\w+)\}/g) || [];
    const seen = new Set();
    const vars = [];
    for (const m of matches) {
        const name = m.slice(1, -1);
        if (!seen.has(name)) {
            seen.add(name);
            vars.push(name);
        }
    }
    return vars;
}

function hideWidget(widget) {
    widget.hidden = true;
}

function showWidget(widget, label) {
    widget.hidden = false;
    widget.label = label;
}

function updateVariableWidgets(node) {
    const folderWidget = node.widgets?.find(w => w.name === "folder_template");
    const filenameWidget = node.widgets?.find(w => w.name === "filename_template");
    if (!folderWidget || !filenameWidget) return;

    const folderVars = parseVariables(folderWidget.value || "");
    const filenameVars = parseVariables(filenameWidget.value || "");
    const folderVarSet = new Set(folderVars);

    // Filename-only vars: exclude any already defined in folder template
    const filenameOnlyVars = filenameVars.filter(v => !folderVarSet.has(v));

    console.log("[FilePathBuilder] Folder vars:", folderVars, "Filename-only vars:", filenameOnlyVars);

    // Show/hide folder_var_ widgets
    for (const widget of node.widgets) {
        const folderMatch = widget.name.match(/^folder_var_(\d+)$/);
        if (folderMatch) {
            const idx = parseInt(folderMatch[1]);
            const inputIndex = node.inputs?.findIndex(inp => inp.name === widget.name);
            const isConnected = inputIndex >= 0 && node.inputs[inputIndex].link != null;

            if (idx <= folderVars.length) {
                showWidget(widget, folderVars[idx - 1]);
            } else if (!isConnected) {
                hideWidget(widget);
                widget.label = widget.name;
            }
        }

        const filenameMatch = widget.name.match(/^filename_var_(\d+)$/);
        if (filenameMatch) {
            const idx = parseInt(filenameMatch[1]);
            const inputIndex = node.inputs?.findIndex(inp => inp.name === widget.name);
            const isConnected = inputIndex >= 0 && node.inputs[inputIndex].link != null;

            if (idx <= filenameOnlyVars.length) {
                showWidget(widget, filenameOnlyVars[idx - 1]);
            } else if (!isConnected) {
                hideWidget(widget);
                widget.label = widget.name;
            }
        }
    }

    const computed = node.computeSize();
    node.setSize([Math.max(computed[0], 400), computed[1]]);
    app.graph.setDirtyCanvas(true);
}

app.registerExtension({
    name: "comfy.fileManagement.dynamicVars",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "FilePathBuilder") return;

        console.log("[FilePathBuilder] Registering node def hooks");

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            onNodeCreated?.apply(this, arguments);

            const node = this;

            // Add a visual separator before filename_template
            const filenameWidget = node.widgets?.find(w => w.name === "filename_template");
            if (filenameWidget) {
                const idx = node.widgets.indexOf(filenameWidget);
                const separator = node.addWidget("label", "separator_filename", "── Filename ──");
                // Move separator before filename_template
                node.widgets.splice(node.widgets.indexOf(separator), 1);
                node.widgets.splice(idx, 0, separator);
            }

            // Watch template fields for changes
            for (const templateName of ["folder_template", "filename_template"]) {
                const widget = node.widgets?.find(w => w.name === templateName);
                if (!widget) continue;

                const origCallback = widget.callback;
                widget.callback = function (value) {
                    origCallback?.apply(this, arguments);
                    updateVariableWidgets(node);
                };

                let currentValue = widget.value;
                Object.defineProperty(widget, "value", {
                    get() { return currentValue; },
                    set(newVal) {
                        currentValue = newVal;
                        updateVariableWidgets(node);
                    },
                    configurable: true,
                });
            }

            // Initial update
            setTimeout(() => updateVariableWidgets(node), 50);
            setTimeout(() => updateVariableWidgets(node), 300);
            setTimeout(() => updateVariableWidgets(node), 1000);
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (data) {
            onConfigure?.apply(this, arguments);
            setTimeout(() => updateVariableWidgets(this), 50);
            setTimeout(() => updateVariableWidgets(this), 300);
            setTimeout(() => updateVariableWidgets(this), 1000);
        };
    },
});
