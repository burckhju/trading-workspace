export type RequestIdentity = Readonly<{
  actorId: string;
  actorName?: string;
}>;

const LOCAL_IDENTITY: RequestIdentity = Object.freeze({
  actorId: '00000000-0000-4000-8000-000000000002',
  actorName: 'Trading Workspace User',
});

let identityProvider: () => RequestIdentity | undefined = () => LOCAL_IDENTITY;

/** Configure the application-level identity source. Feature clients never set identity headers. */
export function configureRequestIdentityProvider(
  provider: () => RequestIdentity | undefined,
): void {
  identityProvider = provider;
}

export function getRequestIdentity(): RequestIdentity | undefined {
  return identityProvider();
}

export function resetRequestIdentityProvider(): void {
  identityProvider = () => LOCAL_IDENTITY;
}
