export interface TaskConfig {
  FleetSize: number;
  StackName: string;
  TimeoutHours: number;
  BlockDeviceVolumeGBRoot: number;
  ContainerImage: string;
  TaskDefinition: string;
  track_config: string;
  model_location: string;
}