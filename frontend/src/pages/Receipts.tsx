import { useParams } from "react-router-dom";
import { ReceiptDetail } from "../components/Receipts/ReceiptDetail";
import { ReceiptList } from "../components/Receipts/ReceiptList";

export function Receipts() {
  const { id } = useParams<{ id: string }>();

  if (id) {
    return <ReceiptDetail receiptId={Number(id)} />;
  }

  return <ReceiptList />;
}
