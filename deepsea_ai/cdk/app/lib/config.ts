export interface TaskConfig {
  FleetSize: number;
  StackName: string;
  ContainerImage: string;
  TaskDefinition: string;
  track_config: string;
  model_location: string;
}