import { fireEvent, render, screen, within } from "@testing-library/react";
import { vi } from "vitest";

import { OrgSwitcher } from "./OrgSwitcher";

describe("OrgSwitcher", () => {
  it("renders org scope first and keeps business/environment as secondary filters", () => {
    const onSelectOrg = vi.fn();
    const onSelectBusiness = vi.fn();
    const onSelectEnvironment = vi.fn();

    render(
      <OrgSwitcher
        orgs={[
          { id: "org_alpha", label: "Alpha Holdings" },
          { id: "org_beta", label: "Beta Ventures" },
        ]}
        activeOrgId="org_alpha"
        onSelectOrg={onSelectOrg}
        businessOptions={[
          { id: "all", label: "All businesses" },
          { id: "limitless", label: "Limitless" },
        ]}
        activeBusinessId="limitless"
        onSelectBusiness={onSelectBusiness}
        environmentOptions={[
          { id: "all", label: "All environments" },
          { id: "production", label: "Production" },
        ]}
        activeEnvironment="production"
        onSelectEnvironment={onSelectEnvironment}
      />,
    );

    expect(screen.getByText("Organization scope")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Alpha Holdings" })).toHaveClass("workspace-switcher__item--active");
    expect(screen.getByRole("tab", { name: "Beta Ventures" })).toBeInTheDocument();

    const businessGroup = screen.getByRole("group", { name: "Business filter" });
    expect(within(businessGroup).getByRole("button", { name: "Limitless" })).toHaveAttribute("aria-pressed", "true");
    expect(within(businessGroup).getByRole("button", { name: "All businesses" })).toHaveAttribute("aria-pressed", "false");

    const environmentGroup = screen.getByRole("group", { name: "Environment filter" });
    expect(within(environmentGroup).getByRole("button", { name: "Production" })).toHaveAttribute("aria-pressed", "true");
    expect(within(environmentGroup).getByRole("button", { name: "All environments" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );

    fireEvent.click(screen.getByRole("tab", { name: "Beta Ventures" }));
    fireEvent.click(within(businessGroup).getByRole("button", { name: "All businesses" }));
    fireEvent.click(within(environmentGroup).getByRole("button", { name: "All environments" }));

    expect(onSelectOrg).toHaveBeenCalledWith("org_beta");
    expect(onSelectBusiness).toHaveBeenCalledWith("all");
    expect(onSelectEnvironment).toHaveBeenCalledWith("all");
  });
});
