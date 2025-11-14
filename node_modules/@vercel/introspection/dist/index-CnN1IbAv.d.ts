//#region src/index.d.ts
declare const introspectApp: (args: {
  dir: string;
  handler: string;
  env: Record<string, string | undefined>;
}) => Promise<{
  routes: ({
    src: string;
    dest: string;
    methods: string[];
  } | {
    handle: string;
    src?: undefined;
    dest?: undefined;
  } | {
    src: string;
    dest: string;
    handle?: undefined;
  })[];
  framework: {
    slug: string;
    version: string | undefined;
  };
}>;
//#endregion
export { introspectApp };