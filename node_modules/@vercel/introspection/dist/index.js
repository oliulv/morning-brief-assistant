import { spawn } from "child_process";
import { existsSync } from "fs";
import { dirname, join } from "path";
import { createRequire } from "module";
import { fileURLToPath } from "url";
import { z } from "zod";

//#region src/index.ts
const require = createRequire(import.meta.url);
const introspectApp = async (args) => {
	const cjsLoaderPath = fileURLToPath(new URL("loaders/cjs.cjs", import.meta.url));
	const esmLoaderPath = new URL("loaders/esm.js", import.meta.url).href;
	const handlerPath = join(args.dir, args.handler);
	let introspectionResult = {
		frameworkSlug: "",
		routes: []
	};
	await new Promise((resolvePromise) => {
		try {
			const child = spawn("node", [
				"-r",
				cjsLoaderPath,
				"--import",
				esmLoaderPath,
				handlerPath
			], {
				stdio: [
					"pipe",
					"pipe",
					"pipe"
				],
				cwd: args.dir,
				env: {
					...process.env,
					...args.env
				}
			});
			child.stdout?.on("data", (data) => {
				try {
					const introspection = JSON.parse(data.toString());
					introspectionResult = z.object({
						frameworkSlug: z.string(),
						routes: z.array(z.object({
							src: z.string(),
							dest: z.string(),
							methods: z.array(z.string())
						}))
					}).parse(introspection);
				} catch (error) {}
			});
			const timeout = setTimeout(() => {
				child.kill("SIGTERM");
			}, 2e3);
			const timeout2 = setTimeout(() => {
				child.kill("SIGKILL");
			}, 3e3);
			child.on("error", (err) => {
				clearTimeout(timeout);
				clearTimeout(timeout2);
				console.log(`Loader error: ${err.message}`);
				resolvePromise(void 0);
			});
			child.on("close", () => {
				clearTimeout(timeout);
				clearTimeout(timeout2);
				resolvePromise(void 0);
			});
		} catch (error) {
			resolvePromise(void 0);
		}
	});
	const routes = [
		{ handle: "filesystem" },
		...introspectionResult.routes,
		{
			src: "/(.*)",
			dest: "/"
		}
	];
	let version;
	if (introspectionResult.frameworkSlug) {
		const frameworkLibPath = require.resolve(`${introspectionResult.frameworkSlug}`, { paths: [args.dir] });
		const findNearestPackageJson = (dir) => {
			const packageJsonPath = join(dir, "package.json");
			if (existsSync(packageJsonPath)) return packageJsonPath;
			const parentDir = dirname(dir);
			if (parentDir === dir) return;
			return findNearestPackageJson(parentDir);
		};
		const nearestPackageJsonPath = findNearestPackageJson(frameworkLibPath);
		if (nearestPackageJsonPath) version = require(nearestPackageJsonPath).version;
	}
	return {
		routes,
		framework: {
			slug: introspectionResult.frameworkSlug,
			version
		}
	};
};

//#endregion
export { introspectApp };