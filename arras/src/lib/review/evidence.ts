import type { Cause, Manifest } from '$lib/manifest/types';
import { displayNode } from '$lib/nodes/display';

export const causeIdentity = (c: Cause) => c.identity ?? [c.kind, c.id ?? '', c.via ?? ''].join('|');
export function causeLabel(m: Manifest, c: Cause): string {
 const target = c.label ?? (c.id ? displayNode(m, c.id).name : 'dependency');
 if (c.via) return `This block uses ${(c.via.startsWith('equation:') ? `equation ${c.via.slice(9)}` : displayNode(m, c.via).name)}, which uses the changed ${target}.`;
 switch (c.kind) {
  case 'own-text-changed': return 'This block was edited';
  case 'dependency-changed': return `${target} changed`;
  case 'dependency-removed': return `${target} is no longer available`;
  case 'dependency-added': return `New dependency: ${target}`;
  case 'dependency-scope-unavailable': return `Cannot identify the full equation for ${target}`;
  case 'dependency-baseline-unavailable': return `The earlier version of ${target} is unavailable. Review the current version once to record it.`;
  case 'preamble-changed': return 'Document definitions or formatting changed';
  case 'basis-changed': return 'The mathematical classification changed';
  case 'document-gone': return 'The document used for acceptance is unavailable';
  default: return c.kind.replaceAll('-', ' ');
 }
}
