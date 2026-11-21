// Exercise the installed Renovate release's rule ordering, including its advisory overrides.
import assert from "node:assert/strict";
import { readFileSync, realpathSync } from "node:fs";
import { dirname } from "node:path";
import { pathToFileURL } from "node:url";

const dist = pathToFileURL(dirname(realpathSync(process.argv[2])) + "/");
const { getConfig } = await import(new URL("config/defaults.js", dist));
const { mergeChildConfig } = await import(new URL("config/utils.js", dist));
const { flattenUpdates } = await import(new URL("workers/repository/updates/flatten.js", dist));
const { checkMinimumReleaseAge } = await import(new URL("util/minimum-release-age.js", dist));
const policy = mergeChildConfig(getConfig(), JSON.parse(readFileSync("renovate.json")));
const daysAgo = (days) => new Date(Date.now() - days * 86400000).toISOString();

assert.equal(checkMinimumReleaseAge(policy, daysAgo(2)).isPending, true);
assert.equal(checkMinimumReleaseAge(policy, daysAgo(3)).isPending, false);
assert.equal(checkMinimumReleaseAge(policy, undefined).isPending, true);

async function decision(name, updateType, newVersion, age, severity) {
    const config = structuredClone(policy);
    config.semanticCommits = "disabled";
    if (severity) {
        config.packageRules.push({
            matchPackageNames: [name],
            isVulnerabilityAlert: true,
            vulnerabilitySeverity: severity,
            force: config.vulnerabilityAlerts,
        });
    }
    const update = {
        updateType, newVersion, newValue: newVersion, newVersionAgeInDays: age,
        newPatch: Number.parseInt(newVersion.split(".")[2], 10),
    };
    const dep = {
        depName: name, packageName: name, datasource: "pypi",
        currentValue: "1.0.0", currentVersion: "1.0.0", updates: [update],
    };
    const [result] = await flattenUpdates(config, {
        pep621: [{ packageFile: "pyproject.toml", deps: [dep] }],
    });
    if (!result) return "held";
    if (result.dependencyDashboardApproval) return "dashboard";
    return result.automerge ? "automatic" : "review";
}

assert.equal(await decision("django", "patch", "1.0.1", 3), "automatic");
assert.equal(await decision("django", "minor", "1.1.0", 29), "held");
assert.equal(await decision("django", "major", "2.0.0", 30), "dashboard");
assert.equal(await decision("django", "minor", "1.1.1", 3), "review");
assert.equal(await decision("ruff", "minor", "1.1.1", 3), "automatic");
assert.equal(await decision("ruff", "major", "2.0.1", 3), "review");
assert.equal(await decision("django", "major", "2.0.0", 0, "HIGH"), "review");
assert.equal(await decision("django", "patch", "1.0.1", 0, "critical"), "review");
assert.equal(await decision("django", "patch", "1.0.1", 2, "medium"), "held");
assert.equal(await decision("django", "patch", "1.0.1", 3, "medium"), "review");
assert.equal(await decision("opentelemetry-sdk", "patch", "1.0.1", 3), "review");
