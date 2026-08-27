import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Button } from "../src/components/ui/Button";
import { Card } from "../src/components/ui/Card";
import { ToggleGroup } from "../src/components/ui/ToggleGroup";

describe("Button", () => {
  // TC-022-01
  // Given a Button with a variant and a label
  // When it renders
  // Then it is a button exposing that name, with a visible focus ring
  it("renders as a button with a visible focus ring", () => {
    // Arrange & Act
    render(<Button variant="primary">Speichern</Button>);

    // Assert
    const button = screen.getByRole("button", { name: "Speichern" });
    expect(button.className).toContain("focus-visible:ring");
  });

  it("forwards native button props instead of swallowing them", () => {
    // Arrange & Act
    render(
      <Button variant="danger" type="submit" disabled>
        Löschen
      </Button>,
    );

    // Assert
    const button = screen.getByRole("button", { name: "Löschen" });
    expect(button).toHaveAttribute("type", "submit");
    expect(button).toBeDisabled();
  });

  it("calls its click handler", async () => {
    // Arrange
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Weiter</Button>);

    // Act
    await userEvent.click(screen.getByRole("button", { name: "Weiter" }));

    // Assert
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

describe("ToggleGroup", () => {
  // TC-022-02
  // Given a labelled toggle group with a selected value
  // When it renders
  // Then the group and the pressed state are exposed, and clicking reports the value
  it("exposes the group label and the pressed option", () => {
    // Arrange & Act
    render(
      <ToggleGroup
        label="Zeitraum"
        options={[
          { value: "week", label: "Woche" },
          { value: "month", label: "Monat" },
        ]}
        value="month"
        onChange={vi.fn()}
      />,
    );

    // Assert
    const group = screen.getByRole("group", { name: "Zeitraum" });
    expect(group).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Monat" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Woche" })).toHaveAttribute("aria-pressed", "false");
  });

  it("reports the clicked option's value", async () => {
    // Arrange
    const onChange = vi.fn();
    render(
      <ToggleGroup
        label="Zeitraum"
        options={[
          { value: "week", label: "Woche" },
          { value: "month", label: "Monat" },
        ]}
        value="month"
        onChange={onChange}
      />,
    );

    // Act
    await userEvent.click(screen.getByRole("button", { name: "Woche" }));

    // Assert
    expect(onChange).toHaveBeenCalledWith("week");
  });
});

describe("Card", () => {
  // TC-022-03
  // Given a Card with a testId, children and an extra className
  // When it renders
  // Then the children are inside it and the caller's class composes with the base
  it("renders its children and composes a caller-supplied className", () => {
    // Arrange & Act
    render(
      <Card testId="demo-card" className="bg-negative-50">
        <p>Inhalt</p>
      </Card>,
    );

    // Assert
    const card = screen.getByTestId("demo-card");
    expect(card).toHaveTextContent("Inhalt");
    expect(card.className).toContain("bg-negative-50");
    expect(card.className).toContain("rounded-card");
  });
});

describe("chart components", () => {
  // TC-022-06
  // Given the two chart component sources
  // When they are read
  // Then neither contains a hardcoded hex colour
  it.each(["src/components/Charts/PriceHistory.tsx", "src/components/Charts/PurchaseStats.tsx"])(
    "declares no hardcoded hex colour in %s",
    (path) => {
      // Arrange
      const source = readFileSync(resolve(__dirname, "..", path), "utf-8");

      // Assert
      expect(source).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    },
  );
});
