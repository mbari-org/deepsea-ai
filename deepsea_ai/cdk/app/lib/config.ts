export interface TaskConfig {
  FleetSize: number;
  StackName: string;
  TimeoutHours: number;
  BlockDeviceVolumeGB: number;
  ContainerImage: string;
  TaskDefinition: string;
  track_config: string;
  model_location: string;
}