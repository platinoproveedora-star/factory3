import path from 'path';
import fs from 'fs';
import { spawnSync } from 'child_process';
import projectContext from '../project-context.json';

const factoryUrl = (process.env.FACTORY_API_URL || projectContext.factory_api_url || '').replace(/\/$/, '');
const writeKey = process.env.FACTORY_WRITE_KEY || '';
const useLocalSkills = process.env.NODE_ENV === 'development' && !writeKey;

const localSkillPaths: Record<string, string> = {
  'vertical_erp_inventory/erp_inventory_dashboard_data': 'factory/skills/internos/vertical_erp_inventory/erp_inventory_dashboard_data',
  'vertical_erp_inventory/erp_inventory_current_stock_report': 'factory/skills/internos/vertical_erp_inventory/erp_inventory_current_stock_report',
  'vertical_erp_inventory/erp_inventory_product_update': 'factory/skills/internos/vertical_erp_inventory/erp_inventory_product_update',
  'vertical_erp_inventory/erp_inventory_product_save': 'factory/skills/internos/vertical_erp_inventory/erp_inventory_product_save',
  'vertical_erp_inventory/erp_inventory_party_save': 'factory/skills/internos/vertical_erp_inventory/erp_inventory_party_save',
  'vertical_erp_inventory/erp_inventory_party_delete': 'factory/skills/internos/vertical_erp_inventory/erp_inventory_party_delete',
  'vertical_erp_inventory/erp_inventory_kardex_list': 'factory/skills/internos/vertical_erp_inventory/erp_inventory_kardex_list',
  'vertical_erp_inventory/erp_inventory_kardex_save': 'factory/skills/internos/vertical_erp_inventory/erp_inventory_kardex_save',
  'vertical_erp_inventory/erp_inventory_kardex_lot_reassign': 'factory/skills/internos/vertical_erp_inventory/erp_inventory_kardex_lot_reassign',
  'vertical_erp_inventory/erp_inventory_lot_stock_report': 'factory/skills/internos/vertical_erp_inventory/erp_inventory_lot_stock_report',
  'vertical_erp_ventas/erp_ventas_remision_list': 'factory/skills/internos/vertical_erp_ventas/erp_ventas_remision_list',
  'vertical_erp_ventas/erp_ventas_remision_detail': 'factory/skills/internos/vertical_erp_ventas/erp_ventas_remision_detail',
  'vertical_erp_ventas/erp_ventas_remision_update': 'factory/skills/internos/vertical_erp_ventas/erp_ventas_remision_update',
  'vertical_erp_ventas/erp_ventas_remision_full_update': 'factory/skills/internos/vertical_erp_ventas/erp_ventas_remision_full_update',
  'vertical_erp_ventas/erp_ventas_remision_cancel': 'factory/skills/internos/vertical_erp_ventas/erp_ventas_remision_cancel',
  'vertical_erp_ventas/erp_ventas_key_product_matrix': 'factory/skills/internos/vertical_erp_ventas/erp_ventas_key_product_matrix',
  'vertical_erp_ventas/erp_ventas_remision_pdf': 'factory/skills/internos/vertical_erp_ventas/erp_ventas_remision_pdf',
  'vertical_erp_ventas/erp_ventas_pedido_list': 'factory/skills/internos/vertical_erp_ventas/erp_ventas_pedido_list',
  'vertical_erp_compras/erp_compras_supplier_list': 'factory/skills/internos/vertical_erp_compras/erp_compras_supplier_list',
  'vertical_erp_compras/erp_compras_product_list': 'factory/skills/internos/vertical_erp_compras/erp_compras_product_list',
  'vertical_erp_compras/erp_compras_purchase_create': 'factory/skills/internos/vertical_erp_compras/erp_compras_purchase_create',
  'vertical_erp_compras/erp_compras_purchase_list': 'factory/skills/internos/vertical_erp_compras/erp_compras_purchase_list',
  'vertical_erp_compras/erp_compras_purchase_cancel': 'factory/skills/internos/vertical_erp_compras/erp_compras_purchase_cancel',
};

export async function runFactorySkill<T>(skill: string, context: Record<string, any>): Promise<T> {
  if (useLocalSkills) {
    return runLocalSkill<T>(skill, context);
  }
  if (!factoryUrl) {
    throw new Error('FACTORY_API_URL requerido para ejecutar skills remotos');
  }

  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (writeKey) headers['X-Write-Key'] = writeKey;
  const res = await fetch(`${factoryUrl}/data/${skill}`, {
    method: 'POST',
    headers,
    cache: 'no-store',
    body: JSON.stringify({
      company_id: projectContext.company_id,
      project_code: projectContext.project_code,
      module_code: projectContext.module_code,
      schema: projectContext.schema,
      inventory_schema: projectContext.inventory_schema,
      schema_inventario: projectContext.schema_inventario,
      sales_schema: projectContext.sales_schema,
      schema_ventas: projectContext.schema_ventas,
      sales_project_code: projectContext.sales_project_code,
      sales_module_code: projectContext.sales_module_code,
      inventory_project_code: projectContext.inventory_project_code,
      inventory_module_code: projectContext.inventory_module_code,
      dry_run: false,
      ...context,
    }),
  });
  const json = await res.json();
  if (!res.ok || json?.ok === false) {
    throw new Error(json?.detail || json?.error || `Factory error ${res.status}`);
  }
  return json as T;
}

function runLocalSkill<T>(skill: string, context: Record<string, any>): T {
  const skillPath = localSkillPaths[skill];
  if (!skillPath) {
    throw new Error(`Skill local no configurado: ${skill}`);
  }
  const repoRoot = path.resolve(process.cwd(), '..', '..', '..', '..', '..', '..');
  const fullSkillPath = path.join(repoRoot, skillPath);
  const childEnv = { ...loadRootEnv(repoRoot), ...process.env };
  const payload = {
    company_id: projectContext.company_id,
    project_code: projectContext.project_code,
    module_code: projectContext.module_code,
    schema: projectContext.schema,
    inventory_schema: projectContext.inventory_schema,
    schema_inventario: projectContext.schema_inventario,
    sales_schema: projectContext.sales_schema,
    schema_ventas: projectContext.schema_ventas,
    sales_project_code: projectContext.sales_project_code,
    sales_module_code: projectContext.sales_module_code,
    inventory_project_code: projectContext.inventory_project_code,
    inventory_module_code: projectContext.inventory_module_code,
    dry_run: false,
    ...context,
  };
  const code = [
    'import json, sys',
    'sys.path.insert(0, sys.argv[1])',
    'import skill',
    'result = skill.run(json.loads(sys.argv[2]))',
    'print(json.dumps(result, ensure_ascii=False))',
  ].join('; ');
  const result = spawnSync('python', ['-c', code, fullSkillPath, JSON.stringify(payload)], {
    cwd: repoRoot,
    env: childEnv,
    encoding: 'utf8',
  });
  if (result.status !== 0) {
    throw new Error((result.stderr || result.stdout || 'Error ejecutando skill local').trim());
  }
  const json = JSON.parse(result.stdout || '{}');
  if (json?.ok === false) {
    throw new Error(json?.error || 'Error ejecutando skill local');
  }
  return json?.data as T;
}

function loadRootEnv(repoRoot: string): Record<string, string> {
  const envPath = path.join(repoRoot, '.env');
  if (!fs.existsSync(envPath)) return {};
  const env: Record<string, string> = {};
  for (const rawLine of fs.readFileSync(envPath, 'utf8').split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const idx = line.indexOf('=');
    if (idx <= 0) continue;
    const key = line.slice(0, idx).trim();
    let value = line.slice(idx + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    env[key] = value;
  }
  return env;
}
