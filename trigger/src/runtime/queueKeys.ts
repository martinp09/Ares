export function queueKey(businessId: string, environment: string): string {
  return `${businessId}:${environment}`;
}

export function marketingQueueKey(businessId: string, environment: string): string {
  return `marketing:${queueKey(businessId, environment)}`;
}

export function leadSequenceQueueKey(
  businessId: string,
  environment: string,
  leadId: string
): string {
  return `${marketingQueueKey(businessId, environment)}:lead:${leadId}`;
}
