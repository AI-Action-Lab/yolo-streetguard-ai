import { ReportTracker } from "../../../components/report-tracker";

type TrackReportPageProps = {
  params: Promise<{ reportId: string }>;
};

export default async function TrackReportPage({ params }: TrackReportPageProps) {
  const { reportId } = await params;
  return <ReportTracker initialReportId={decodeURIComponent(reportId)} />;
}
