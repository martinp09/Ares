export function queueKey(businessId: string, environment: string): string {
  return `${businessId}:${environment}`;
}
