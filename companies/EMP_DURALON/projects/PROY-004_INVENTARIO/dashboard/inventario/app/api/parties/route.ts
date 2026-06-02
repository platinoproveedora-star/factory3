import { NextResponse } from 'next/server';
import { getSupabase } from '../../../lib/supabase';

export const dynamic = 'force-dynamic';

export async function GET(req: Request) {
  try {
    const type = new URL(req.url).searchParams.get('type');
    let query = getSupabase().from('erp_parties').select('*').order('party_name', { ascending: true });
    if (type === 'customer') query = query.in('party_type', ['customer', 'both']);
    if (type === 'supplier') query = query.in('party_type', ['supplier', 'both']);
    const { data, error } = await query;
    if (error) throw error;
    return NextResponse.json({ ok: true, data: data || [] });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error cargando terceros' }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const row = {
      folio: body.folio,
      party_type: body.party_type,
      party_name: body.party_name,
      legal_name: body.legal_name || null,
      rfc: body.rfc || null,
      phone: body.phone || null,
      email: body.email || null,
      address: body.address || null,
      active: body.active !== false,
    };
    const { data, error } = await getSupabase().from('erp_parties').insert(row).select().single();
    if (error) throw error;
    return NextResponse.json({ ok: true, data });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error guardando tercero' }, { status: 500 });
  }
}

export async function PATCH(req: Request) {
  try {
    const body = await req.json();
    if (!body.id) {
      return NextResponse.json({ ok: false, error: 'id es requerido' }, { status: 400 });
    }
    if (!String(body.party_name || '').trim()) {
      return NextResponse.json({ ok: false, error: 'nombre es requerido' }, { status: 400 });
    }
    const row = {
      party_name: String(body.party_name).trim(),
      legal_name: body.legal_name || null,
      rfc: body.rfc || null,
      phone: body.phone || null,
      email: body.email || null,
      address: body.address || null,
      active: body.active !== false,
      updated_at: new Date().toISOString(),
    };
    const { data, error } = await getSupabase().from('erp_parties').update(row).eq('id', body.id).select().single();
    if (error) throw error;
    return NextResponse.json({ ok: true, data });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error actualizando tercero' }, { status: 500 });
  }
}
